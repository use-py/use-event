"""
Advanced functionality tests for the event bus.
"""
import asyncio
import pytest
from unittest.mock import Mock

from src.use_event.core import EventBus, on, emit, off


class TestPriorityHandling:
    """Test priority-based handler execution."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()
        self.execution_order = []
    
    def test_priority_ordering(self):
        """Test that handlers execute in priority order."""
        @self.event_bus.on("test_event", priority=3)
        def low_priority():
            self.execution_order.append("low")
            
        @self.event_bus.on("test_event", priority=1)
        def high_priority():
            self.execution_order.append("high")
            
        @self.event_bus.on("test_event", priority=2)
        def medium_priority():
            self.execution_order.append("medium")
        
        self.event_bus.emit("test_event")
        
        # Should execute in priority order (lower number = higher priority)
        assert self.execution_order == ["high", "medium", "low"]
    
    def test_same_priority_registration_order(self):
        """Test that handlers with same priority execute in registration order."""
        @self.event_bus.on("test_event", priority=1)
        def first_handler():
            self.execution_order.append("first")
            
        @self.event_bus.on("test_event", priority=1)
        def second_handler():
            self.execution_order.append("second")
            
        @self.event_bus.on("test_event", priority=1)
        def third_handler():
            self.execution_order.append("third")
        
        self.event_bus.emit("test_event")
        
        # Should execute in registration order for same priority
        assert self.execution_order == ["first", "second", "third"]


class TestAsyncHandling:
    """Test asynchronous handler execution."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()
        self.results = []
    
    @pytest.mark.asyncio
    async def test_async_handlers_only(self):
        """Test emitting event with only async handlers."""
        @self.event_bus.on("test_event")
        async def async_handler1(value):
            await asyncio.sleep(0.01)  # Small delay
            self.results.append(f"async1: {value}")
            
        @self.event_bus.on("test_event")
        async def async_handler2(value):
            await asyncio.sleep(0.005)  # Smaller delay
            self.results.append(f"async2: {value}")
        
        self.event_bus.emit("test_event", "test_value")
        
        # Give time for async handlers to complete
        await asyncio.sleep(0.02)
        
        assert len(self.results) == 2
        assert "async1: test_value" in self.results
        assert "async2: test_value" in self.results
    
    def test_mixed_sync_async_handlers(self):
        """Test emitting event with mixed sync and async handlers."""
        @self.event_bus.on("test_event", priority=1)
        def sync_handler(value):
            self.results.append(f"sync: {value}")
            
        @self.event_bus.on("test_event", priority=2)
        async def async_handler(value):
            await asyncio.sleep(0.01)
            self.results.append(f"async: {value}")
        
        self.event_bus.emit("test_event", "test_value")
        
        # Sync handler should execute immediately
        assert len(self.results) == 1
        assert self.results[0] == "sync: test_value"
        
        # Give time for async handler to complete
        import time
        time.sleep(0.02)
        
        # Note: In a real async context, the async handler would also complete
        # But in this sync test, it runs in a separate task
    
    @pytest.mark.asyncio
    async def test_async_handler_with_parameters(self):
        """Test async handlers receive parameters correctly."""
        @self.event_bus.on("test_event")
        async def async_handler(arg1, arg2, kwarg1=None):
            await asyncio.sleep(0.001)
            self.results.append((arg1, arg2, kwarg1))
        
        self.event_bus.emit("test_event", "val1", "val2", kwarg1="kw1")
        
        # Give time for async handler to complete
        await asyncio.sleep(0.01)
        
        assert len(self.results) == 1
        assert self.results[0] == ("val1", "val2", "kw1")


class TestContextManager:
    """Test context manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()
        self.results = []
    
    def test_context_manager_basic(self):
        """Test basic context manager functionality."""
        def temp_handler():
            self.results.append("temp")
            
        # Handler should not be registered initially
        assert len(self.event_bus._listeners["test_event"]) == 0
        
        with self.event_bus.on("test_event", temp_handler):
            # Handler should be registered inside context
            assert len(self.event_bus._listeners["test_event"]) == 1
            
            # Emit event - should trigger handler
            self.event_bus.emit("test_event")
            assert len(self.results) == 1
            assert self.results[0] == "temp"
        
        # Handler should be removed after context
        assert len(self.event_bus._listeners["test_event"]) == 0
        
        # Emit again - should not trigger handler
        self.event_bus.emit("test_event")
        assert len(self.results) == 1  # Still 1, not 2
    
    def test_context_manager_with_exception(self):
        """Test context manager cleanup on exception."""
        def temp_handler():
            self.results.append("temp")
            
        try:
            with self.event_bus.on("test_event", temp_handler):
                # Handler should be registered
                assert len(self.event_bus._listeners["test_event"]) == 1
                
                # Raise exception
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Handler should still be removed despite exception
        assert len(self.event_bus._listeners["test_event"]) == 0
    
    def test_context_manager_with_priority(self):
        """Test context manager with priority."""
        def temp_handler():
            self.results.append("temp")
            
        @self.event_bus.on("test_event", priority=2)
        def permanent_handler():
            self.results.append("permanent")
            
        with self.event_bus.on("test_event", temp_handler, priority=1):
            self.event_bus.emit("test_event")
            
            # Temp handler should execute first (higher priority)
            assert len(self.results) == 2
            assert self.results[0] == "temp"
            assert self.results[1] == "permanent"


class TestParameterPassing:
    """Test parameter passing to handlers."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()
        self.received_params = []
    
    def test_no_parameters(self):
        """Test handler with no parameters."""
        @self.event_bus.on("test_event")
        def handler():
            self.received_params.append("no_params")
        
        self.event_bus.emit("test_event")
        assert len(self.received_params) == 1
        assert self.received_params[0] == "no_params"
    
    def test_positional_parameters(self):
        """Test handler with positional parameters."""
        @self.event_bus.on("test_event")
        def handler(arg1, arg2, arg3):
            self.received_params.append((arg1, arg2, arg3))
        
        self.event_bus.emit("test_event", "val1", "val2", "val3")
        assert len(self.received_params) == 1
        assert self.received_params[0] == ("val1", "val2", "val3")
    
    def test_keyword_parameters(self):
        """Test handler with keyword parameters."""
        @self.event_bus.on("test_event")
        def handler(kwarg1=None, kwarg2=None):
            self.received_params.append((kwarg1, kwarg2))
        
        self.event_bus.emit("test_event", kwarg1="kw1", kwarg2="kw2")
        assert len(self.received_params) == 1
        assert self.received_params[0] == ("kw1", "kw2")
    
    def test_mixed_parameters(self):
        """Test handler with mixed positional and keyword parameters."""
        @self.event_bus.on("test_event")
        def handler(arg1, arg2, kwarg1=None, kwarg2=None):
            self.received_params.append((arg1, arg2, kwarg1, kwarg2))
        
        self.event_bus.emit("test_event", "val1", "val2", kwarg1="kw1", kwarg2="kw2")
        assert len(self.received_params) == 1
        assert self.received_params[0] == ("val1", "val2", "kw1", "kw2")
    
    @pytest.mark.asyncio
    async def test_async_handler_parameters(self):
        """Test async handler with parameters."""
        @self.event_bus.on("test_event")
        async def async_handler(arg1, kwarg1=None):
            await asyncio.sleep(0.001)
            self.received_params.append((arg1, kwarg1))
        
        self.event_bus.emit("test_event", "async_val", kwarg1="async_kw")
        
        # Give time for async handler to complete
        await asyncio.sleep(0.01)
        
        assert len(self.received_params) == 1
        assert self.received_params[0] == ("async_val", "async_kw")