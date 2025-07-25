"""
Core event bus implementation with EventHandler and EventBus classes.
"""
import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Union, Any


logger = logging.getLogger(__name__)


@dataclass
class EventHandler:
    """Event handler wrapper that stores function, priority and async detection."""
    func: Callable
    priority: int = 0
    is_async: bool = field(init=False)
    registration_order: int = field(init=False)
    
    def __post_init__(self):
        """Auto-detect if the function is async and set registration order."""
        self.is_async = asyncio.iscoroutinefunction(self.func)
        # Registration order will be set by EventBus when adding handler
        self.registration_order = 0


class EventBus:
    """Main event bus class for managing event listeners and emission."""
    
    def __init__(self):
        """Initialize event bus with empty listeners storage."""
        self._listeners: Dict[str, List[EventHandler]] = defaultdict(list)
        self._registration_counter = 0
    
    def _add_handler(self, event_name: str, handler: Callable, priority: int = 0) -> EventHandler:
        """Internal method to add a handler to an event."""
        event_handler = EventHandler(func=handler, priority=priority)
        event_handler.registration_order = self._registration_counter
        self._registration_counter += 1
        
        self._listeners[event_name].append(event_handler)
        return event_handler
    
    def _remove_handler(self, event_name: str, handler: Callable) -> bool:
        """Internal method to remove a specific handler from an event."""
        if event_name not in self._listeners:
            return False
            
        handlers = self._listeners[event_name]
        for i, event_handler in enumerate(handlers):
            if event_handler.func == handler:
                handlers.pop(i)
                return True
        return False
    
    def _get_sorted_handlers(self, event_name: str) -> List[EventHandler]:
        """Get handlers for an event sorted by priority and registration order."""
        if event_name not in self._listeners:
            return []
            
        handlers = self._listeners[event_name][:]  # Create a copy
        # Sort by priority first, then by registration order
        handlers.sort(key=lambda h: (h.priority, h.registration_order))
        return handlers
    
    def on(self, event_name: str, handler: Optional[Callable] = None, priority: int = 0) -> Union[Callable, 'EventContextManager']:
        """
        Register an event listener. Supports decorator mode and context manager mode.
        
        Args:
            event_name: Name of the event to listen to
            handler: Handler function (optional for decorator mode)
            priority: Priority of the handler (lower number = higher priority)
            
        Returns:
            - If handler is provided: EventContextManager for with statement
            - If handler is None: Decorator function
        """
        def decorator(func: Callable) -> Callable:
            """Decorator function for @event.on("event_name") syntax."""
            self._add_handler(event_name, func, priority)
            return func
        
        if handler is None:
            # Decorator mode: @event.on("event_name")
            return decorator
        else:
            # Context manager mode: with event.on("event_name", handler)
            return EventContextManager(self, event_name, handler, priority)
    
    def emit(self, event_name: str, *args, **kwargs) -> None:
        """
        Emit an event, triggering all registered handlers.
        Supports both sync and async handlers with mixed execution.
        
        Args:
            event_name: Name of the event to emit
            *args: Positional arguments to pass to handlers
            **kwargs: Keyword arguments to pass to handlers
        """
        handlers = self._get_sorted_handlers(event_name)
        if not handlers:
            return
        
        # Separate sync and async handlers
        sync_handlers = [h for h in handlers if not h.is_async]
        async_handlers = [h for h in handlers if h.is_async]
        
        # Execute sync handlers first
        self._execute_sync_handlers(sync_handlers, *args, **kwargs)
        
        # Execute async handlers if any exist
        if async_handlers:
            # Check if we're already in an async context
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, create task for async handlers
                asyncio.create_task(self._execute_async_handlers(async_handlers, *args, **kwargs))
            except RuntimeError:
                # No running loop, create a new thread to run async handlers
                # This prevents blocking the current thread
                import threading
                def run_async_handlers():
                    asyncio.run(self._execute_async_handlers(async_handlers, *args, **kwargs))
                
                thread = threading.Thread(target=run_async_handlers, daemon=True)
                thread.start()
    
    def _execute_sync_handlers(self, handlers: List[EventHandler], *args, **kwargs) -> None:
        """Execute synchronous handlers with error isolation."""
        for handler in handlers:
            try:
                handler.func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Error in sync handler {handler.func.__name__}: {e}")
    
    async def _execute_async_handlers(self, handlers: List[EventHandler], *args, **kwargs) -> None:
        """Execute asynchronous handlers concurrently with error isolation."""
        if not handlers:
            return
            
        tasks = []
        for handler in handlers:
            try:
                task = asyncio.create_task(handler.func(*args, **kwargs))
                tasks.append(task)
            except Exception as e:
                logger.warning(f"Error creating task for {handler.func.__name__}: {e}")
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    handler_name = handlers[i].func.__name__ if i < len(handlers) else "unknown"
                    logger.warning(f"Error in async handler {handler_name}: {result}")
    
    def off(self, event_name: str, handler: Optional[Callable] = None) -> None:
        """
        Remove event listener(s).
        
        Args:
            event_name: Name of the event
            handler: Specific handler to remove. If None, removes all handlers for the event.
        """
        if handler is None:
            # Remove all handlers for the event
            if event_name in self._listeners:
                self._listeners[event_name].clear()
        else:
            # Remove specific handler (silently handle if not found)
            self._remove_handler(event_name, handler)


class EventContextManager:
    """Context manager for temporary event listeners."""
    
    def __init__(self, event_bus: EventBus, event_name: str, handler: Callable, priority: int = 0):
        self.event_bus = event_bus
        self.event_name = event_name
        self.handler = handler
        self.priority = priority
        
    def __enter__(self):
        """Register the handler when entering context."""
        self.event_bus._add_handler(self.event_name, self.handler, self.priority)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Remove the handler when exiting context."""
        self.event_bus._remove_handler(self.event_name, self.handler)

# Global default event bus instance
_default_event_bus = EventBus()


# Module-level convenience functions using the default instance
def on(event_name: str, handler: Optional[Callable] = None, priority: int = 0) -> Union[Callable, 'EventContextManager']:
    """
    Register an event listener using the default event bus.
    
    Args:
        event_name: Name of the event to listen to
        handler: Handler function (optional for decorator mode)
        priority: Priority of the handler (lower number = higher priority)
        
    Returns:
        - If handler is provided: EventContextManager for with statement
        - If handler is None: Decorator function
    """
    return _default_event_bus.on(event_name, handler, priority)


def emit(event_name: str, *args, **kwargs) -> None:
    """
    Emit an event using the default event bus.
    
    Args:
        event_name: Name of the event to emit
        *args: Positional arguments to pass to handlers
        **kwargs: Keyword arguments to pass to handlers
    """
    _default_event_bus.emit(event_name, *args, **kwargs)


def off(event_name: str, handler: Optional[Callable] = None) -> None:
    """
    Remove event listener(s) using the default event bus.
    
    Args:
        event_name: Name of the event
        handler: Specific handler to remove. If None, removes all handlers for the event.
    """
    _default_event_bus.off(event_name, handler)


# Export list
__all__ = [
    'EventBus',
    'EventHandler', 
    'EventContextManager',
    'on',
    'emit', 
    'off'
]