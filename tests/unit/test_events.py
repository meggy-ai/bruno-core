"""Tests for event system."""

import pytest

from bruno_core.events.bus import EventBus
from bruno_core.events.handlers import AsyncEventHandler, EventHandler
from bruno_core.events.types import Event, EventType, MessageEvent


@pytest.mark.asyncio
class TestEventBus:
    """Tests for EventBus."""

    async def test_publish_and_subscribe(self):
        """Test basic publish/subscribe."""
        bus = EventBus()
        received_events = []

        async def handler(event):
            received_events.append(event)

        bus.subscribe(EventType.MESSAGE_RECEIVED, handler)

        event = MessageEvent(
            event_type=EventType.MESSAGE_RECEIVED,
            message_id="msg-123",
            user_id="user-123",
            conversation_id="conv-123",
            role="user",
        )

        await bus.publish(event)

        assert len(received_events) == 1
        assert received_events[0].message_id == "msg-123"

    async def test_multiple_handlers(self):
        """Test multiple handlers for same event."""
        bus = EventBus()
        call_counts = {"handler1": 0, "handler2": 0}

        async def handler1(event):
            call_counts["handler1"] += 1

        async def handler2(event):
            call_counts["handler2"] += 1

        bus.subscribe(EventType.MESSAGE_RECEIVED, handler1)
        bus.subscribe(EventType.MESSAGE_RECEIVED, handler2)

        event = MessageEvent(
            event_type=EventType.MESSAGE_RECEIVED,
            message_id="msg-123",
            user_id="user-123",
            conversation_id="conv-123",
            role="user",
        )

        await bus.publish(event)

        assert call_counts["handler1"] == 1
        assert call_counts["handler2"] == 1

    async def test_wildcard_subscription(self):
        """Test wildcard subscription."""
        bus = EventBus()
        received_events = []

        async def wildcard_handler(event):
            received_events.append(event)

        bus.subscribe_all(wildcard_handler)

        # Publish different event types
        event1 = Event(event_type=EventType.MESSAGE_RECEIVED)
        event2 = Event(event_type=EventType.SESSION_STARTED)

        await bus.publish(event1)
        await bus.publish(event2)

        assert len(received_events) == 2

    async def test_unsubscribe(self):
        """Test unsubscribing handler."""
        bus = EventBus()
        call_count = 0

        async def handler(event):
            nonlocal call_count
            call_count += 1

        bus.subscribe(EventType.MESSAGE_RECEIVED, handler)

        event = Event(event_type=EventType.MESSAGE_RECEIVED)
        await bus.publish(event)

        bus.unsubscribe(EventType.MESSAGE_RECEIVED, handler)
        await bus.publish(event)

        # Should only be called once (before unsubscribe)
        assert call_count == 1

    async def test_event_history(self):
        """Test event history tracking."""
        bus = EventBus(enable_history=True, max_history=5)

        for i in range(10):
            event = Event(event_type=EventType.MESSAGE_RECEIVED)
            await bus.publish(event)

        history = bus.get_history()

        # Should only keep last 5
        assert len(history) == 5

    async def test_handler_priority(self):
        """Test handler priority."""
        bus = EventBus()
        execution_order = []

        async def low_priority(event):
            execution_order.append("low")

        async def high_priority(event):
            execution_order.append("high")

        bus.subscribe(EventType.MESSAGE_RECEIVED, low_priority, priority=1)
        bus.subscribe(EventType.MESSAGE_RECEIVED, high_priority, priority=10)

        event = Event(event_type=EventType.MESSAGE_RECEIVED)
        await bus.publish(event)

        # High priority should execute first
        assert execution_order == ["high", "low"]

    async def test_get_statistics(self):
        """Test event bus statistics."""
        bus = EventBus()

        async def handler(event):
            pass

        bus.subscribe(EventType.MESSAGE_RECEIVED, handler)

        event = Event(event_type=EventType.MESSAGE_RECEIVED)
        await bus.publish(event)

        stats = bus.get_statistics()
        assert stats["published"] == 1
        assert stats["handled"] == 1


class TestEventHandlers:
    """Tests for event handlers."""

    def test_event_handler(self):
        """Test EventHandler base class."""

        class TestHandler(EventHandler):
            def __init__(self):
                super().__init__()
                self.handled = []

            def get_event_types(self):
                return [EventType.MESSAGE_RECEIVED]

            def handle(self, event):
                self.handled.append(event)

        handler = TestHandler()
        event = Event(event_type=EventType.MESSAGE_RECEIVED)

        handler(event)

        assert len(handler.handled) == 1

    @pytest.mark.asyncio
    async def test_async_event_handler(self):
        """Test AsyncEventHandler base class."""

        class TestAsyncHandler(AsyncEventHandler):
            def __init__(self):
                super().__init__()
                self.handled = []

            def get_event_types(self):
                return [EventType.MESSAGE_RECEIVED]

            async def handle(self, event):
                self.handled.append(event)

        handler = TestAsyncHandler()
        event = Event(event_type=EventType.MESSAGE_RECEIVED)

        await handler(event)

        assert len(handler.handled) == 1

    def test_handler_filtering(self):
        """Test handler should_handle filtering."""

        class SelectiveHandler(EventHandler):
            def get_event_types(self):
                return [EventType.MESSAGE_RECEIVED]

            def handle(self, event):
                pass

        handler = SelectiveHandler()

        correct_event = Event(event_type=EventType.MESSAGE_RECEIVED)
        wrong_event = Event(event_type=EventType.SESSION_STARTED)

        assert handler.should_handle(correct_event) is True
        assert handler.should_handle(wrong_event) is False
