"""
Event Bus implementation.

Provides pub/sub mechanism for decoupled component communication.
"""

import asyncio
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Set

from bruno_core.events.types import Event, EventType
from bruno_core.utils.logging import get_logger

logger = get_logger(__name__)


class EventBus:
    """
    Event bus for publish/subscribe pattern.

    Features:
    - Async event handlers
    - Event type filtering
    - Wildcard subscriptions
    - Event history
    - Handler prioritization

    Example:
        >>> bus = EventBus()
        >>> 
        >>> async def on_message(event):
        ...     print(f"Message: {event.data}")
        >>> 
        >>> bus.subscribe(EventType.MESSAGE_RECEIVED, on_message)
        >>> await bus.publish(MessageEvent(event_type=EventType.MESSAGE_RECEIVED, ...))
    """

    def __init__(self, enable_history: bool = False, max_history: int = 100):
        """
        Initialize event bus.

        Args:
            enable_history: Enable event history tracking
            max_history: Maximum events to keep in history
        """
        self.enable_history = enable_history
        self.max_history = max_history

        # Handlers by event type
        self._handlers: Dict[EventType, List[Callable]] = defaultdict(list)
        
        # Wildcard handlers (receive all events)
        self._wildcard_handlers: List[Callable] = []

        # Event history
        self._history: List[Event] = []

        # Statistics
        self._stats = {
            "published": 0,
            "handled": 0,
            "errors": 0,
        }

        logger.info("event_bus_initialized", history_enabled=enable_history)

    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], Any],
        priority: int = 0,
    ) -> None:
        """
        Subscribe to an event type.

        Args:
            event_type: Event type to subscribe to
            handler: Handler function (can be sync or async)
            priority: Handler priority (higher = earlier execution)
        """
        # Store with priority
        self._handlers[event_type].append((priority, handler))
        
        # Sort by priority (descending)
        self._handlers[event_type].sort(key=lambda x: x[0], reverse=True)

        logger.info(
            "handler_subscribed",
            event_type=event_type.value,
            handler=handler.__name__,
            priority=priority,
        )

    def subscribe_all(self, handler: Callable[[Event], Any]) -> None:
        """
        Subscribe to all events (wildcard).

        Args:
            handler: Handler function for all events
        """
        self._wildcard_handlers.append(handler)
        logger.info("wildcard_handler_subscribed", handler=handler.__name__)

    def unsubscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], Any],
    ) -> bool:
        """
        Unsubscribe from an event type.

        Args:
            event_type: Event type
            handler: Handler to remove

        Returns:
            True if handler was found and removed
        """
        if event_type not in self._handlers:
            return False

        original_count = len(self._handlers[event_type])
        self._handlers[event_type] = [
            (p, h) for p, h in self._handlers[event_type] if h != handler
        ]

        removed = len(self._handlers[event_type]) < original_count
        if removed:
            logger.info(
                "handler_unsubscribed",
                event_type=event_type.value,
                handler=handler.__name__,
            )

        return removed

    def unsubscribe_all(self, handler: Callable[[Event], Any]) -> bool:
        """
        Unsubscribe wildcard handler.

        Args:
            handler: Handler to remove

        Returns:
            True if handler was found and removed
        """
        if handler in self._wildcard_handlers:
            self._wildcard_handlers.remove(handler)
            logger.info("wildcard_handler_unsubscribed", handler=handler.__name__)
            return True
        return False

    async def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribed handlers.

        Args:
            event: Event to publish
        """
        try:
            self._stats["published"] += 1

            # Add to history
            if self.enable_history:
                self._history.append(event)
                if len(self._history) > self.max_history:
                    self._history.pop(0)

            logger.debug(
                "event_published",
                event_type=event.event_type,
                event_id=event.event_id,
            )

            # Get handlers for this event type
            handlers = self._handlers.get(event.event_type, [])
            
            # Add wildcard handlers
            wildcard_handlers = [(0, h) for h in self._wildcard_handlers]
            all_handlers = handlers + wildcard_handlers

            # Execute handlers
            for priority, handler in all_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                    
                    self._stats["handled"] += 1

                except Exception as e:
                    self._stats["errors"] += 1
                    logger.error(
                        "handler_error",
                        event_type=event.event_type,
                        handler=handler.__name__,
                        error=str(e),
                    )

        except Exception as e:
            logger.error("publish_error", event_type=event.event_type, error=str(e))

    async def publish_many(self, events: List[Event]) -> None:
        """
        Publish multiple events.

        Args:
            events: List of events to publish
        """
        for event in events:
            await self.publish(event)

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: Optional[int] = None,
    ) -> List[Event]:
        """
        Get event history.

        Args:
            event_type: Optional filter by event type
            limit: Optional limit number of events

        Returns:
            List of events (most recent first)
        """
        if not self.enable_history:
            return []

        history = self._history[::-1]  # Reverse to get most recent first

        if event_type:
            history = [e for e in history if e.event_type == event_type]

        if limit:
            history = history[:limit]

        return history

    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()
        logger.info("event_history_cleared")

    def get_subscriber_count(self, event_type: Optional[EventType] = None) -> int:
        """
        Get number of subscribers.

        Args:
            event_type: Optional specific event type

        Returns:
            Number of subscribers
        """
        if event_type:
            return len(self._handlers.get(event_type, []))
        else:
            total = sum(len(handlers) for handlers in self._handlers.values())
            return total + len(self._wildcard_handlers)

    def list_event_types(self) -> List[EventType]:
        """
        List all event types with subscribers.

        Returns:
            List of event types
        """
        return list(self._handlers.keys())

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get event bus statistics.

        Returns:
            Dict with statistics
        """
        return {
            **self._stats,
            "subscribers": self.get_subscriber_count(),
            "event_types": len(self._handlers),
            "wildcard_handlers": len(self._wildcard_handlers),
            "history_size": len(self._history) if self.enable_history else 0,
        }

    def reset_statistics(self) -> None:
        """Reset statistics counters."""
        self._stats = {
            "published": 0,
            "handled": 0,
            "errors": 0,
        }
        logger.info("statistics_reset")
