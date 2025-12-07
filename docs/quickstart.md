# Quick Start Guide

Get started with bruno-core in minutes.

## Installation

### From PyPI (Recommended)

```bash
pip install bruno-core
```

### From Source

```bash
git clone https://github.com/meggy-ai/bruno-core.git
cd bruno-core
pip install -e .
```

### Development Installation

```bash
pip install -e ".[dev]"  # Includes test dependencies
```

## Basic Usage

### 1. Create Mock Implementations

For this quickstart, we'll create simple mock implementations. In production, use real implementations from bruno-llm and bruno-memory packages.

```python
# mock_llm.py
from bruno_core.interfaces import LLMInterface
from bruno_core.models import Message

class MockLLM(LLMInterface):
    async def generate(self, messages: list[Message], **kwargs) -> str:
        return "Hello! I'm a mock assistant."
    
    async def stream(self, messages: list[Message], **kwargs):
        response = await self.generate(messages, **kwargs)
        for char in response:
            yield char
    
    def get_token_count(self, text: str) -> int:
        return len(text.split())
    
    def list_models(self) -> list[str]:
        return ["mock-model"]
```

```python
# mock_memory.py
from bruno_core.interfaces import MemoryInterface
from bruno_core.models import Message, MemoryEntry

class MockMemory(MemoryInterface):
    def __init__(self):
        self.messages = {}
    
    async def store_message(self, message: Message, user_id: str, conversation_id: str):
        key = f"{user_id}:{conversation_id}"
        if key not in self.messages:
            self.messages[key] = []
        self.messages[key].append(message)
    
    async def retrieve_context(self, user_id: str, query: str, limit: int = 10, conversation_id: str = None):
        key = f"{user_id}:{conversation_id}"
        return self.messages.get(key, [])[-limit:]
    
    async def search_memories(self, user_id: str, query: str, limit: int = 5):
        return []
    
    async def clear_conversation(self, user_id: str, conversation_id: str):
        key = f"{user_id}:{conversation_id}"
        self.messages.pop(key, None)
```

### 2. Create an Assistant

```python
# main.py
import asyncio
from bruno_core.base import BaseAssistant
from bruno_core.models import Message, MessageRole
from mock_llm import MockLLM
from mock_memory import MockMemory

async def main():
    # Initialize components
    llm = MockLLM()
    memory = MockMemory()
    
    # Create assistant
    assistant = BaseAssistant(llm=llm, memory=memory)
    await assistant.initialize()
    
    # Process a message
    user_message = Message(
        role=MessageRole.USER,
        content="Hello, how are you?"
    )
    
    response = await assistant.process_message(
        message=user_message,
        user_id="user-123",
        conversation_id="conv-456"
    )
    
    print(f"Assistant: {response.text}")
    
    # Cleanup
    await assistant.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Run It

```bash
python main.py
```

Output:
```
Assistant: Hello! I'm a mock assistant.
```

## Adding Abilities

Abilities add functionality to your assistant. Here's how to create and register one:

```python
from bruno_core.base import BaseAbility
from bruno_core.models import AbilityMetadata, AbilityRequest, AbilityResponse

class GreetingAbility(BaseAbility):
    def get_metadata(self) -> AbilityMetadata:
        return AbilityMetadata(
            name="greeting",
            description="Greet users warmly",
            version="1.0.0",
            examples=["say hello", "greet me"]
        )
    
    async def execute_action(self, request: AbilityRequest) -> AbilityResponse:
        return AbilityResponse(
            request_id=request.id,
            ability_name="greeting",
            action=request.action,
            success=True,
            message=f"Hello {request.user_id}! Nice to meet you!",
            data={"greeted": True}
        )
    
    def get_supported_actions(self) -> list[str]:
        return ["greet", "hello"]

# Register ability
greeting = GreetingAbility()
await assistant.register_ability(greeting)
```

## Using the Registry System

For plugin-based architecture, register abilities via entry points:

```python
# setup.py
from setuptools import setup

setup(
    name="my-bruno-plugins",
    packages=["my_abilities"],
    entry_points={
        "bruno.abilities": [
            "greeting = my_abilities.greeting:GreetingAbility",
            "timer = my_abilities.timer:TimerAbility",
        ]
    }
)
```

Then discover plugins automatically:

```python
from bruno_core.registry import AbilityRegistry

registry = AbilityRegistry()
registry.discover_plugins()  # Auto-discovers from entry points

# Get instances
greeting = registry.get_instance("greeting")
await assistant.register_ability(greeting)
```

## Configuration

Use configuration models for type-safe settings:

```python
from bruno_core.models import BrunoConfig, LLMConfig, MemoryConfig

config = BrunoConfig(
    llm=LLMConfig(
        provider="openai",
        model="gpt-4",
        temperature=0.7,
        max_tokens=1000
    ),
    memory=MemoryConfig(
        backend="sqlite",
        max_context_messages=20,
        database_path="./bruno.db"
    )
)
```

## Event System

Subscribe to events for monitoring and logging:

```python
from bruno_core.events import EventBus, EventType

bus = EventBus(enable_history=True)

async def on_message(event):
    print(f"Message received: {event.message_id}")

bus.subscribe(EventType.MESSAGE_RECEIVED, on_message)

# Events are published automatically by BaseAssistant
# Or publish manually:
await bus.publish(message_event)
```

## Next Steps

- Read the [Architecture Guide](architecture.md) to understand the design
- Learn how to [Create Custom Abilities](guides/creating_abilities.md)
- Integrate your own [LLM Provider](guides/custom_llm.md)
- Build a [Custom Memory Backend](guides/memory_backends.md)
- Check out [Examples](../examples/) for more patterns

## Common Issues

### Import Errors

If you see import errors, ensure bruno-core is installed:
```bash
pip list | grep bruno-core
```

### Async Errors

All bruno-core APIs are async. Always use `await` and run within an event loop:
```python
import asyncio
asyncio.run(main())
```

### Type Errors

bruno-core uses type hints. Install mypy for type checking:
```bash
pip install mypy
mypy your_code.py
```

## Production Usage

For production deployments:

1. Use real LLM providers (bruno-llm package)
2. Use persistent memory (bruno-memory package)
3. Enable structured logging
4. Add error handling and retries
5. Monitor with the event system
6. Use configuration files

See our [deployment examples](../examples/) for production patterns.
