"""
Core functionality tests for the event bus.
"""
import asyncio
import pytest
from unittest.mock import Mock

from src.use_event.core import EventBus, EventHandler, on, emit, off


class TestEventHandler:
    """Test EventHandler class functionality."""
    
    def test_sync_handler_creation(self):
        """Test creating EventHandler with sync function."""
        def sync_func():
            pass
            
        handler = EventHandler(func=sync_func, priority=1)
        assert handler.func == sync_func
        assert handler.priority == 1
        assert handler.is_async is False
        assert handler.registration_order == 0
    
    def test_async_handler_creation(self):
        """Test creating EventHandler with async function."""
        async def async_func():
            pass
            
        handler = EventHandler(func=async_func, priority=2)
        assert handler.func == async_func
        assert handler.priority == 2
        assert handler.is_async is True
        assert handler.registration_order == 0


class TestEventBusBasic:
    """Test basic EventBus functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()
    
    def test_event_bus_initialization(self):
        """Test EventBus initialization."""
        assert len(self.event_bus._listeners) == 0
        assert self.event_bus._registration_counter == 0
    
    def test_add_handler_internal(self):
        """Test internal _add_handler method."""
        def test_func():
            pass
            
        handler = self.event_bus._add_handler("test_event", test_func, priority=1)
        
        assert handler.func == test_func
        assert handler.priority == 1
        assert handler.registration_order == 0
        assert len(self.event_bus._listeners["test_event"]) == 1
        assert self.event_bus._registration_counter == 1
    
    def test_remove_handler_internal(self):
        """Test internal _remove_handler method."""
        def test_func():
            pass
            
        # Add handler first
        self.event_bus._add_handler("test_event", test_func)
        assert len(self.event_bus._listeners["test_event"]) == 1
        
        # Remove handler
        result = self.event_bus._remove_handler("test_event", test_func)
        assert result is True
        assert len(self.event_bus._listeners["test_event"]) == 0
        
        # Try to remove non-existent handler
        result = self.event_bus._remove_handler("test_event", test_func)
        assert result is False


class TestEventRegistration:
    """Test event registration functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()
        self.mock_handler = Mock()
    
    def test_on_method_direct_registration(self):
        """Test direct handler registration with on method."""
        context_manager = self.event_bus.on("test_event", self.mock_handler)
        
        # Should return context manager
        from src.use_event.core import EventContextManager
        assert isinstance(context_manager, EventContextManager)
        
        # Handler should not be registered yet (only when entering context)
        assert len(self.event_bus._listeners["test_event"]) == 0
    
    def test_on_method_decorator_mode(self):
        """Test decorator mode registration."""
        @self.event_bus.on("test_event")
        def test_handler():
            return "test"
            
        # Handler should be registered immediately
        assert len(self.event_bus._listeners["test_event"]) == 1
        assert self.event_bus._listeners["test_event"][0].func == test_handler
        
        # Function should still be callable
        assert test_handler() == "test"
    
    def test_on_method_with_priority(self):
        """Test registration with priority."""
        @self.event_bus.on("test_event", priority=5)
        def high_priority():
            pass
            
        @self.event_bus.on("test_event", priority=1)
        def low_priority():
            pass
            
        handlers = self.event_bus._get_sorted_handlers("test_event")
        assert len(handlers) == 2
        assert handlers[0].func == low_priority  # Lower number = higher priority
        assert handlers[1].func == high_priority


class TestEventEmission:
    """Test event emission functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()
        self.results = []
    
    def test_emit_no_handlers(self):
        """Test emitting event with no handlers."""
        # Should not raise any exceptions
        self.event_bus.emit("non_existent_event")
    
    def test_emit_sync_handlers(self):
        """Test emitting event with sync handlers."""
        @self.event_bus.on("test_event")
        def handler1(value):
            self.results.append(f"handler1: {value}")
            
        @self.event_bus.on("test_event")
        def handler2(value):
            self.results.append(f"handler2: {value}")
        
        self.event_bus.emit("test_event", "test_value")
        
        assert len(self.results) == 2
        assert "handler1: test_value" in self.results
        assert "handler2: test_value" in self.results
    
    def test_emit_with_args_kwargs(self):
        """Test emitting event with both args and kwargs."""
        @self.event_bus.on("test_event")
        def handler(arg1, arg2, kwarg1=None, kwarg2=None):
            self.results.append((arg1, arg2, kwarg1, kwarg2))
        
        self.event_bus.emit("test_event", "val1", "val2", kwarg1="kw1", kwarg2="kw2")
        
        assert len(self.results) == 1
        assert self.results[0] == ("val1", "val2", "kw1", "kw2")


class TestModuleLevelFunctions:
    """Test module-level convenience functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear any existing handlers from default instance
        from src.use_event.core import _default_event_bus
        _default_event_bus._listeners.clear()
        _default_event_bus._registration_counter = 0
        self.results = []
    
    def test_module_on_decorator(self):
        """Test module-level on function as decorator."""
        @on("test_event")
        def test_handler():
            self.results.append("called")
            
        emit("test_event")
        assert len(self.results) == 1
        assert self.results[0] == "called"
    
    def test_module_off_function(self):
        """Test module-level off function."""
        @on("test_event")
        def test_handler():
            self.results.append("called")
            
        # Emit once - should work
        emit("test_event")
        assert len(self.results) == 1
        
        # Remove handler
        off("test_event", test_handler)
        
        # Emit again - should not call handler
        emit("test_event")
        assert len(self.results) == 1  # Still 1, not 2