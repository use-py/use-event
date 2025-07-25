"""
Error handling tests for the event bus.
"""
import asyncio
import pytest
import logging
from unittest.mock import Mock, patch

from src.use_event.core import EventBus, on, emit, off


class TestSyncHandlerErrorIsolation:
    """Test error isolation for synchronous handlers."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()
        self.results = []
        self.logger_mock = Mock()
    
    def test_single_handler_exception(self):
        """Test that a single handler exception is caught and logged."""
        @self.event_bus.on("test_event")
        def failing_handler():
            raise ValueError("Test error")
        
        with patch('src.use_event.core.logger') as mock_logger:
            # Should not raise exception
            self.event_bus.emit("test_event")
            
            # Should log the error
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[0][0]
            assert "Error in sync handler failing_handler" in call_args
            assert "Test error" in call_args
    
    def test_multiple_handlers_one_fails(self):
        """Test that one failing handler doesn't affect others."""
        @self.event_bus.on("test_event", priority=1)
        def working_handler1():
            self.results.append("handler1")
            
        @self.event_bus.on("test_event", priority=2)
        def failing_handler():
            self.results.append("failing")
            raise RuntimeError("Handler failed")
            
        @self.event_bus.on("test_event", priority=3)
        def working_handler2():
            self.results.append("handler2")
        
        with patch('src.use_event.core.logger'):
            self.event_bus.emit("test_event")
        
        # All handlers should have been called, including the failing one
        assert len(self.results) == 3
        assert "handler1" in self.results
        assert "failing" in self.results
        assert "handler2" in self.results
    
    def test_handler_exception_with_parameters(self):
        """Test handler exception when parameters are passed."""
        @self.event_bus.on("test_event")
        def failing_handler(arg1, kwarg1=None):
            self.results.append(f"received: {arg1}, {kwarg1}")
            raise TypeError("Parameter error")
            
        @self.event_bus.on("test_event")
        def working_handler(arg1, kwarg1=None):
            self.results.append(f"working: {arg1}, {kwarg1}")
        
        with patch('src.use_event.core.logger') as mock_logger:
            self.event_bus.emit("test_event", "test_arg", kwarg1="test_kwarg")
            
            # Both handlers should have received parameters
            assert len(self.results) == 2
            assert "received: test_arg, test_kwarg" in self.results
            assert "working: test_arg, test_kwarg" in self.results
            
            # Error should be logged
            mock_logger.warning.assert_called_once()
    
    def test_different_exception_types(self):
        """Test handling of different exception types."""
        @self.event_bus.on("test_event", priority=1)
        def value_error_handler():
            raise ValueError("Value error")
            
        @self.event_bus.on("test_event", priority=2)
        def type_error_handler():
            raise TypeError("Type error")
            
        @self.event_bus.on("test_event", priority=3)
        def runtime_error_handler():
            raise RuntimeError("Runtime error")
        
        with patch('src.use_event.core.logger') as mock_logger:
            self.event_bus.emit("test_event")
            
            # Should log all three errors
            assert mock_logger.warning.call_count == 3
            
            # Check that different error types are logged
            call_args_list = [call[0][0] for call in mock_logger.warning.call_args_list]
            assert any("Value error" in call for call in call_args_list)
            assert any("Type error" in call for call in call_args_list)
            assert any("Runtime error" in call for call in call_args_list)


class TestAsyncHandlerErrorIsolation:
    """Test error isolation for asynchronous handlers."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()
        self.results = []
    
    @pytest.mark.asyncio
    async def test_single_async_handler_exception(self):
        """Test that a single async handler exception is caught and logged."""
        @self.event_bus.on("test_event")
        async def failing_async_handler():
            await asyncio.sleep(0.001)
            raise ValueError("Async test error")
        
        with patch('src.use_event.core.logger') as mock_logger:
            self.event_bus.emit("test_event")
            
            # Give time for async handler to complete
            await asyncio.sleep(0.01)
            
            # Should log the error
            mock_logger.warning.assert_called()
            call_args = mock_logger.warning.call_args_list
            assert any("Error in async handler failing_async_handler" in str(call) for call in call_args)
    
    @pytest.mark.asyncio
    async def test_multiple_async_handlers_one_fails(self):
        """Test that one failing async handler doesn't affect others."""
        @self.event_bus.on("test_event", priority=1)
        async def working_async_handler1():
            await asyncio.sleep(0.001)
            self.results.append("async1")
            
        @self.event_bus.on("test_event", priority=2)
        async def failing_async_handler():
            await asyncio.sleep(0.001)
            self.results.append("failing_async")
            raise RuntimeError("Async handler failed")
            
        @self.event_bus.on("test_event", priority=3)
        async def working_async_handler2():
            await asyncio.sleep(0.001)
            self.results.append("async2")
        
        with patch('src.use_event.core.logger'):
            self.event_bus.emit("test_event")
            
            # Give time for async handlers to complete
            await asyncio.sleep(0.02)
        
        # All handlers should have been called
        assert len(self.results) == 3
        assert "async1" in self.results
        assert "failing_async" in self.results
        assert "async2" in self.results
    
    @pytest.mark.asyncio
    async def test_async_handler_task_creation_error(self):
        """Test error handling when task creation fails."""
        # Create a mock handler that will cause task creation to fail
        mock_handler = Mock()
        mock_handler.__name__ = "mock_handler"
        
        # Make the mock raise an exception when called
        mock_handler.side_effect = Exception("Task creation error")
        
        # Manually add handler to bypass normal registration
        from src.use_event.core import EventHandler
        handler = EventHandler(func=mock_handler, priority=0)
        handler.is_async = True  # Force it to be treated as async
        handler.registration_order = 0
        self.event_bus._listeners["test_event"].append(handler)
        
        with patch('src.use_event.core.logger') as mock_logger:
            self.event_bus.emit("test_event")
            
            # Give time for async processing
            await asyncio.sleep(0.01)
            
            # Should log task creation error
            mock_logger.warning.assert_called()
            call_args = mock_logger.warning.call_args[0][0]
            assert "Error creating task for mock_handler" in call_args
    
    @pytest.mark.asyncio
    async def test_mixed_sync_async_handlers_with_errors(self):
        """Test error isolation in mixed sync/async handler scenarios."""
        @self.event_bus.on("test_event", priority=1)
        def failing_sync_handler():
            self.results.append("sync_failing")
            raise ValueError("Sync error")
            
        @self.event_bus.on("test_event", priority=2)
        def working_sync_handler():
            self.results.append("sync_working")
            
        @self.event_bus.on("test_event", priority=3)
        async def failing_async_handler():
            await asyncio.sleep(0.001)
            self.results.append("async_failing")
            raise RuntimeError("Async error")
            
        @self.event_bus.on("test_event", priority=4)
        async def working_async_handler():
            await asyncio.sleep(0.001)
            self.results.append("async_working")
        
        with patch('src.use_event.core.logger') as mock_logger:
            self.event_bus.emit("test_event")
            
            # Give time for async handlers to complete
            await asyncio.sleep(0.02)
        
        # All handlers should have been called
        assert len(self.results) == 4
        assert "sync_failing" in self.results
        assert "sync_working" in self.results
        assert "async_failing" in self.results
        assert "async_working" in self.results
        
        # Should log both sync and async errors
        assert mock_logger.warning.call_count >= 2


class TestBoundaryConditions:
    """Test boundary conditions and edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()
        self.results = []
    
    def test_emit_nonexistent_event(self):
        """Test emitting an event with no handlers."""
        # Should not raise any exceptions
        self.event_bus.emit("nonexistent_event")
        self.event_bus.emit("nonexistent_event", "arg1", kwarg1="value")
    
    def test_remove_nonexistent_handler(self):
        """Test removing a handler that doesn't exist."""
        def dummy_handler():
            pass
            
        # Should not raise exceptions
        self.event_bus.off("nonexistent_event", dummy_handler)
        self.event_bus.off("nonexistent_event")
    
    def test_handler_modifies_event_bus_during_execution(self):
        """Test handler that modifies the event bus during execution."""
        @self.event_bus.on("test_event")
        def self_removing_handler():
            self.results.append("removing_self")
            self.event_bus.off("test_event", self_removing_handler)
            
        @self.event_bus.on("test_event")
        def normal_handler():
            self.results.append("normal")
        
        # First emission
        self.event_bus.emit("test_event")
        assert len(self.results) == 2
        assert "removing_self" in self.results
        assert "normal" in self.results
        
        # Second emission - self-removing handler should be gone
        self.results.clear()
        self.event_bus.emit("test_event")
        assert len(self.results) == 1
        assert "normal" in self.results
    
    def test_handler_adds_new_handler_during_execution(self):
        """Test handler that adds a new handler during execution."""
        def new_handler():
            self.results.append("new_handler")
            
        @self.event_bus.on("test_event")
        def adding_handler():
            self.results.append("adding")
            # Use decorator mode to immediately register the new handler
            @self.event_bus.on("test_event")
            def temp_new_handler():
                self.results.append("new_handler")
        
        # First emission
        self.event_bus.emit("test_event")
        assert len(self.results) == 1
        assert "adding" in self.results
        
        # Second emission - new handler should be present
        self.results.clear()
        self.event_bus.emit("test_event")
        assert len(self.results) == 2
        assert "adding" in self.results
        assert "new_handler" in self.results
    
    def test_context_manager_exception_cleanup(self):
        """Test that context manager cleans up even when handler raises exception."""
        def failing_temp_handler():
            self.results.append("temp_failing")
            raise ValueError("Temp handler error")
            
        @self.event_bus.on("test_event")
        def permanent_handler():
            self.results.append("permanent")
        
        # Use context manager with failing handler
        with patch('src.use_event.core.logger'):
            with self.event_bus.on("test_event", failing_temp_handler):
                self.event_bus.emit("test_event")
        
        # Both handlers should have been called
        assert len(self.results) == 2
        assert "temp_failing" in self.results
        assert "permanent" in self.results
        
        # Temp handler should be removed after context
        self.results.clear()
        self.event_bus.emit("test_event")
        assert len(self.results) == 1
        assert "permanent" in self.results


class TestModuleLevelErrorHandling:
    """Test error handling with module-level functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear any existing handlers from default instance
        from src.use_event.core import _default_event_bus
        _default_event_bus._listeners.clear()
        _default_event_bus._registration_counter = 0
        self.results = []
    
    def test_module_level_handler_exception(self):
        """Test error handling with module-level on/emit functions."""
        @on("test_event")
        def failing_module_handler():
            self.results.append("module_failing")
            raise ValueError("Module handler error")
            
        @on("test_event")
        def working_module_handler():
            self.results.append("module_working")
        
        with patch('src.use_event.core.logger') as mock_logger:
            emit("test_event")
            
            # Both handlers should have been called
            assert len(self.results) == 2
            assert "module_failing" in self.results
            assert "module_working" in self.results
            
            # Error should be logged
            mock_logger.warning.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_module_level_async_handler_exception(self):
        """Test async error handling with module-level functions."""
        @on("test_event")
        async def failing_async_module_handler():
            await asyncio.sleep(0.001)
            self.results.append("async_module_failing")
            raise RuntimeError("Async module handler error")
            
        @on("test_event")
        async def working_async_module_handler():
            await asyncio.sleep(0.001)
            self.results.append("async_module_working")
        
        with patch('src.use_event.core.logger') as mock_logger:
            emit("test_event")
            
            # Give time for async handlers to complete
            await asyncio.sleep(0.02)
            
            # Both handlers should have been called
            assert len(self.results) == 2
            assert "async_module_failing" in self.results
            assert "async_module_working" in self.results
            
            # Error should be logged
            mock_logger.warning.assert_called()


class TestLoggingConfiguration:
    """Test logging configuration and output."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()
    
    def test_logger_name(self):
        """Test that the logger uses the correct name."""
        from src.use_event.core import logger
        assert logger.name == "src.use_event.core"
    
    def test_error_message_format(self):
        """Test the format of error messages."""
        @self.event_bus.on("test_event")
        def test_handler():
            raise ValueError("Test message")
        
        with patch('src.use_event.core.logger') as mock_logger:
            self.event_bus.emit("test_event")
            
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[0][0]
            
            # Should include handler name and error message
            assert "Error in sync handler test_handler" in call_args
            assert "Test message" in call_args
    
    @pytest.mark.asyncio
    async def test_async_error_message_format(self):
        """Test the format of async error messages."""
        @self.event_bus.on("test_event")
        async def async_test_handler():
            await asyncio.sleep(0.001)
            raise RuntimeError("Async test message")
        
        with patch('src.use_event.core.logger') as mock_logger:
            self.event_bus.emit("test_event")
            
            # Give time for async handler to complete
            await asyncio.sleep(0.02)
            
            mock_logger.warning.assert_called()
            call_args = mock_logger.warning.call_args[0][0]
            
            # Should include handler name and error message
            assert "Error in async handler async_test_handler" in call_args
            assert "Async test message" in call_args