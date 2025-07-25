"""
use-event: A Vue.js-like event bus library for Python

A lightweight event bus library that provides simple event publishing and subscription
with support for decorators, context managers, priority configuration, and mixed
sync/async execution.

Example usage:
    from use_event import on, emit, off
    
    # Decorator mode
    @on("user_login")
    def handle_login(user_id):
        print(f"User {user_id} logged in")
    
    # Context manager mode
    def temp_handler(data):
        print(f"Temporary handler: {data}")
    
    with on("temp_event", temp_handler):
        emit("temp_event", "test data")
    
    # Emit events
    emit("user_login", user_id=123)
    
    # Remove handlers
    off("user_login", handle_login)
"""

from .core import (
    EventBus,
    EventHandler,
    EventContextManager,
    on,
    emit,
    off
)

__version__ = "0.1.6"
__author__ = "MicLon <jcnd@163.com>"
__license__ = "MIT"

__all__ = [
    'EventBus',
    'EventHandler',
    'EventContextManager', 
    'on',
    'emit',
    'off'
]