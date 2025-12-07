"""
Event Handling Example

Demonstrates the bruno-core event system.
"""

import asyncio
from bruno_core.base import BaseAssistant
from bruno_core.events import (
    EventBus,
    EventHandler,
    AsyncEventHandler,
    MessageEvent,
    AbilityEvent,
    ErrorEvent,
    SystemEvent,
)
from bruno_core.models import Message, MessageRole

# Use mock implementations
import sys
sys.path.append('.')
from examples.basic_assistant import MockLLM, MockMemory


class MessageLogger(EventHandler):
    """Log all messages."""
    
    def __init__(self):
        self.messages_logged = 0
    
    def handle(self, event: MessageEvent):
        """Handle message events."""
        print(f"📝 [MessageLogger] {event.message.role.value}: {event.message.content[:50]}...")
        self.messages_logged += 1


class AbilityMonitor(EventHandler):
    """Monitor ability execution."""
    
    def __init__(self):
        self.executions = []
    
    def handle(self, event: AbilityEvent):
        """Handle ability events."""
        print(f"⚙️  [AbilityMonitor] Ability '{event.ability_name}' - {event.event_type}")
        self.executions.append({
            "ability": event.ability_name,
            "type": event.event_type,
            "timestamp": event.timestamp,
        })


class ErrorTracker(EventHandler):
    """Track errors."""
    
    def __init__(self):
        self.errors = []
    
    def handle(self, event: ErrorEvent):
        """Handle error events."""
        print(f"❌ [ErrorTracker] Error: {event.error_message}")
        self.errors.append({
            "message": event.error_message,
            "type": event.error_type,
            "timestamp": event.timestamp,
        })


class AsyncNotificationHandler(AsyncEventHandler):
    """Send async notifications (e.g., to external services)."""
    
    def __init__(self):
        self.notifications_sent = 0
    
    async def handle_async(self, event):
        """Handle events asynchronously."""
        # Simulate async operation (API call, database write, etc.)
        await asyncio.sleep(0.1)
        
        print(f"🔔 [AsyncNotificationHandler] Sent notification for {event.event_type}")
        self.notifications_sent += 1


class MetricsCollector(AsyncEventHandler):
    """Collect metrics from all events."""
    
    def __init__(self):
        self.metrics = {
            "total_events": 0,
            "events_by_type": {},
            "events_by_hour": {},
        }
    
    async def handle_async(self, event):
        """Collect metrics."""
        self.metrics["total_events"] += 1
        
        # Count by type
        event_type = event.event_type
        self.metrics["events_by_type"][event_type] = \
            self.metrics["events_by_type"].get(event_type, 0) + 1
        
        # Count by hour
        hour = event.timestamp.hour
        self.metrics["events_by_hour"][hour] = \
            self.metrics["events_by_hour"].get(hour, 0) + 1
    
    def get_summary(self) -> dict:
        """Get metrics summary."""
        return {
            "total_events": self.metrics["total_events"],
            "unique_event_types": len(self.metrics["events_by_type"]),
            "most_common_type": max(
                self.metrics["events_by_type"].items(),
                key=lambda x: x[1],
                default=("none", 0)
            )[0],
        }


async def basic_event_example():
    """Basic event handling example."""
    print("1️⃣  Basic Event Handling")
    print("=" * 60)
    
    # Create event bus
    event_bus = EventBus()
    
    # Create handlers
    message_logger = MessageLogger()
    ability_monitor = AbilityMonitor()
    error_tracker = ErrorTracker()
    
    # Subscribe handlers
    event_bus.subscribe("message.received", message_logger)
    event_bus.subscribe("message.sent", message_logger)
    event_bus.subscribe("ability.started", ability_monitor)
    event_bus.subscribe("ability.completed", ability_monitor)
    event_bus.subscribe("error.occurred", error_tracker)
    
    print("✅ Event bus configured with 3 handlers\n")
    
    # Create assistant with event bus
    llm = MockLLM()
    memory = MockMemory()
    assistant = BaseAssistant(llm=llm, memory=memory, event_bus=event_bus)
    await assistant.initialize()
    
    # Process some messages
    messages = [
        "Hello!",
        "How are you?",
        "What can you do?",
    ]
    
    for msg_text in messages:
        msg = Message(role=MessageRole.USER, content=msg_text)
        await assistant.process_message(msg, "user1", "conv1")
        print()  # Blank line for readability
    
    # Show handler statistics
    print(f"\n📊 Handler Statistics:")
    print(f"   Messages logged: {message_logger.messages_logged}")
    print(f"   Ability executions: {len(ability_monitor.executions)}")
    print(f"   Errors tracked: {len(error_tracker.errors)}")
    
    await assistant.shutdown()


async def async_handler_example():
    """Async event handler example."""
    print("\n\n2️⃣  Async Event Handlers")
    print("=" * 60)
    
    event_bus = EventBus()
    
    # Create async handlers
    notifier = AsyncNotificationHandler()
    metrics = MetricsCollector()
    
    # Subscribe to all events
    event_bus.subscribe("message.received", notifier)
    event_bus.subscribe("message.sent", notifier)
    event_bus.subscribe("ability.started", metrics)
    event_bus.subscribe("ability.completed", metrics)
    event_bus.subscribe("message.received", metrics)
    event_bus.subscribe("message.sent", metrics)
    
    print("✅ Async handlers configured\n")
    
    # Create assistant
    llm = MockLLM()
    memory = MockMemory()
    assistant = BaseAssistant(llm=llm, memory=memory, event_bus=event_bus)
    await assistant.initialize()
    
    # Process messages
    for i in range(3):
        msg = Message(role=MessageRole.USER, content=f"Test message {i+1}")
        await assistant.process_message(msg, "user2", "conv2")
    
    # Show async handler results
    print(f"\n📊 Async Handler Results:")
    print(f"   Notifications sent: {notifier.notifications_sent}")
    print(f"   Metrics summary: {metrics.get_summary()}")
    
    await assistant.shutdown()


async def custom_events_example():
    """Custom event types example."""
    print("\n\n3️⃣  Custom Event Types")
    print("=" * 60)
    
    event_bus = EventBus()
    
    # Define custom event handler
    class CustomEventHandler(EventHandler):
        def __init__(self):
            self.custom_events = []
        
        def handle(self, event):
            print(f"🎯 [CustomHandler] Received: {event.event_type}")
            self.custom_events.append(event)
    
    handler = CustomEventHandler()
    
    # Subscribe to custom events
    event_bus.subscribe("custom.user.login", handler)
    event_bus.subscribe("custom.user.logout", handler)
    event_bus.subscribe("custom.data.processed", handler)
    
    # Emit custom events
    print("\n📤 Emitting custom events...")
    
    await event_bus.emit(SystemEvent(
        event_type="custom.user.login",
        component="auth",
        data={"user_id": "alice", "ip": "192.168.1.1"}
    ))
    
    await event_bus.emit(SystemEvent(
        event_type="custom.data.processed",
        component="processor",
        data={"records": 1000, "duration": 5.2}
    ))
    
    await event_bus.emit(SystemEvent(
        event_type="custom.user.logout",
        component="auth",
        data={"user_id": "alice", "session_duration": 3600}
    ))
    
    print(f"\n📊 Custom Events Received: {len(handler.custom_events)}")


async def event_filtering_example():
    """Event filtering and pattern matching."""
    print("\n\n4️⃣  Event Filtering")
    print("=" * 60)
    
    event_bus = EventBus()
    
    # Handler that filters events
    class FilteringHandler(EventHandler):
        def __init__(self, keyword: str):
            self.keyword = keyword
            self.matched = 0
        
        def handle(self, event: MessageEvent):
            if hasattr(event, 'message') and self.keyword.lower() in event.message.content.lower():
                print(f"✅ [Filter:{self.keyword}] Matched: {event.message.content}")
                self.matched += 1
    
    # Create filters for different keywords
    urgent_filter = FilteringHandler("urgent")
    help_filter = FilteringHandler("help")
    question_filter = FilteringHandler("?")
    
    # Subscribe filters
    event_bus.subscribe("message.received", urgent_filter)
    event_bus.subscribe("message.received", help_filter)
    event_bus.subscribe("message.received", question_filter)
    
    # Create assistant
    llm = MockLLM()
    memory = MockMemory()
    assistant = BaseAssistant(llm=llm, memory=memory, event_bus=event_bus)
    await assistant.initialize()
    
    # Send messages
    messages = [
        "This is urgent!",
        "I need help with something",
        "How does this work?",
        "Just saying hello",
        "Urgent help needed!",
    ]
    
    print("\n📤 Processing messages...\n")
    for msg_text in messages:
        msg = Message(role=MessageRole.USER, content=msg_text)
        await assistant.process_message(msg, "user3", "conv3")
    
    # Show filter results
    print(f"\n📊 Filter Results:")
    print(f"   'urgent' matches: {urgent_filter.matched}")
    print(f"   'help' matches: {help_filter.matched}")
    print(f"   '?' matches: {question_filter.matched}")
    
    await assistant.shutdown()


async def main():
    """Run all event examples."""
    print("🤖 Bruno Core - Event Handling Examples")
    print("=" * 60)
    
    await basic_event_example()
    await async_handler_example()
    await custom_events_example()
    await event_filtering_example()
    
    print("\n\n✅ All event examples completed!")
    print("\n💡 Key Takeaways:")
    print("   - Use EventBus for decoupled communication")
    print("   - EventHandler for sync operations")
    print("   - AsyncEventHandler for async operations")
    print("   - Subscribe to specific event types")
    print("   - Create custom events for your needs")
    print("   - Filter events in handlers for targeted processing")


if __name__ == "__main__":
    asyncio.run(main())
