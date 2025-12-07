"""
Event Handler base classes.

Provides base classes for creating event handlers.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional

from bruno_core.events.types import Event, EventType
from bruno_core.utils.logging import get_logger

logger = get_logger(__name__)


class EventHandler(ABC):
    """
    Base class for synchronous event handlers.

    Subclasses should implement handle() method.

    Example:
        >>> class MessageLogger(EventHandler):
        ...     def get_event_types(self):
        ...         return [EventType.MESSAGE_RECEIVED]
        ...
        ...     def handle(self, event):
        ...         print(f"Message: {event.message_id}")
    """

    def __init__(self):
        """Initialize event handler."""
        self.enabled = True
        logger.info("handler_created", handler=self.__class__.__name__)

    @abstractmethod
    def get_event_types(self) -> List[EventType]:
        """
        Get list of event types this handler subscribes to.

        Returns:
            List of EventType values
        """
        pass

    @abstractmethod
    def handle(self, event: Event) -> Any:
        """
        Handle an event.

        Args:
            event: Event to handle

        Returns:
            Optional result
        """
        pass

    def should_handle(self, event: Event) -> bool:
        """
        Check if this handler should process the event.

        Override to add custom filtering logic.

        Args:
            event: Event to check

        Returns:
            True if should handle
        """
        if not self.enabled:
            return False

        return event.event_type in self.get_event_types()

    def __call__(self, event: Event) -> Any:
        """
        Make handler callable.

        Args:
            event: Event to handle

        Returns:
            Handler result
        """
        if self.should_handle(event):
            try:
                return self.handle(event)
            except Exception as e:
                logger.error(
                    "handler_error",
                    handler=self.__class__.__name__,
                    event_type=event.event_type,
                    error=str(e),
                )
                raise
        return None


class AsyncEventHandler(ABC):
    """
    Base class for async event handlers.

    Subclasses should implement handle() method.

    Example:
        >>> class MessageProcessor(AsyncEventHandler):
        ...     def get_event_types(self):
        ...         return [EventType.MESSAGE_RECEIVED]
        ...
        ...     async def handle(self, event):
        ...         await process_message(event.message_id)
    """

    def __init__(self):
        """Initialize async event handler."""
        self.enabled = True
        logger.info("async_handler_created", handler=self.__class__.__name__)

    @abstractmethod
    def get_event_types(self) -> List[EventType]:
        """
        Get list of event types this handler subscribes to.

        Returns:
            List of EventType values
        """
        pass

    @abstractmethod
    async def handle(self, event: Event) -> Any:
        """
        Handle an event asynchronously.

        Args:
            event: Event to handle

        Returns:
            Optional result
        """
        pass

    def should_handle(self, event: Event) -> bool:
        """
        Check if this handler should process the event.

        Override to add custom filtering logic.

        Args:
            event: Event to check

        Returns:
            True if should handle
        """
        if not self.enabled:
            return False

        return event.event_type in self.get_event_types()

    async def __call__(self, event: Event) -> Any:
        """
        Make handler callable.

        Args:
            event: Event to handle

        Returns:
            Handler result
        """
        if self.should_handle(event):
            try:
                return await self.handle(event)
            except Exception as e:
                logger.error(
                    "async_handler_error",
                    handler=self.__class__.__name__,
                    event_type=event.event_type,
                    error=str(e),
                )
                raise
        return None


class FilteredEventHandler(EventHandler):
    """
    Event handler with metadata filtering.

    Allows filtering events based on metadata values.

    Example:
        >>> handler = FilteredEventHandler(
        ...     event_types=[EventType.MESSAGE_RECEIVED],
        ...     filters={"user_id": "user_123"}
        ... )
    """

    def __init__(self, event_types: List[EventType], filters: Optional[dict] = None):
        """
        Initialize filtered handler.

        Args:
            event_types: List of event types to handle
            filters: Dict of metadata key-value pairs to filter on
        """
        super().__init__()
        self.event_types = event_types
        self.filters = filters or {}

    def get_event_types(self) -> List[EventType]:
        """Get event types."""
        return self.event_types

    def should_handle(self, event: Event) -> bool:
        """
        Check if event matches filters.

        Args:
            event: Event to check

        Returns:
            True if passes filters
        """
        if not super().should_handle(event):
            return False

        # Check metadata filters
        for key, value in self.filters.items():
            if event.metadata.get(key) != value:
                return False

        return True

    def handle(self, event: Event) -> Any:
        """
        Handle event.

        Override in subclass.

        Args:
            event: Event to handle
        """
        pass
