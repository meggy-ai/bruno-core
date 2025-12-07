# Bruno Core Examples

This directory contains practical examples demonstrating bruno-core capabilities.

## Running Examples

All examples are standalone Python scripts. Run them with:

```bash
python examples/<example_name>.py
```

## Available Examples

### 1. Basic Assistant (`basic_assistant.py`)
The simplest possible bruno-core setup.

**Demonstrates:**
- Creating a basic assistant
- Mock LLM and memory implementations
- Processing messages
- Health checks and statistics

**Run:**
```bash
python examples/basic_assistant.py
```

### 2. Custom Ability (`custom_ability.py`)
Creating and using custom abilities.

**Demonstrates:**
- Implementing `BaseAbility`
- Defining ability metadata and parameters
- Registering abilities with the assistant
- Direct ability execution vs. assistant integration
- Calculator and Timer ability examples

**Run:**
```bash
python examples/custom_ability.py
```

### 3. Custom LLM (`custom_llm.py`)
Implementing custom LLM providers.

**Demonstrates:**
- Implementing `LLMInterface`
- Basic LLM with generate and stream methods
- Advanced LLM with rate limiting and retry logic
- Token counting and model listing
- Streaming responses

**Run:**
```bash
python examples/custom_llm.py
```

### 4. Memory Usage (`memory_usage.py`)
Different memory backend patterns.

**Demonstrates:**
- Simple in-memory storage
- Semantic memory with embeddings (concept)
- Multiple conversations per user
- Memory search and retrieval
- Conversation management (clear, list, etc.)

**Run:**
```bash
python examples/memory_usage.py
```

### 5. Event Handling (`event_handling.py`)
Using the event system.

**Demonstrates:**
- Creating event handlers
- Subscribing to events
- Sync and async event handlers
- Custom event types
- Event filtering and pattern matching
- Metrics collection via events

**Run:**
```bash
python examples/event_handling.py
```

## Example Structure

Each example follows this pattern:

```python
"""
Example Title

Brief description of what this demonstrates.
"""

import asyncio
from bruno_core import ...

# Implementation classes
class CustomImplementation:
    pass

# Demo functions
async def demo_function():
    # Setup
    # Execute
    # Show results
    # Cleanup

async def main():
    # Run all demos
    pass

if __name__ == "__main__":
    asyncio.run(main())
```

## Integration with Your Project

These examples use mock implementations for portability. In your project:

1. **Replace Mock LLM** with real provider (OpenAI, Claude, Ollama):
```python
from openai import AsyncOpenAI
from bruno_core.interfaces import LLMInterface

class OpenAILLM(LLMInterface):
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def generate(self, messages, **kwargs):
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": m.role.value, "content": m.content} for m in messages]
        )
        return response.choices[0].message.content
```

2. **Replace Mock Memory** with real backend (PostgreSQL, Redis, ChromaDB):
```python
import psycopg2
from bruno_core.interfaces import MemoryInterface

class PostgresMemory(MemoryInterface):
    def __init__(self, connection_string: str):
        self.conn = psycopg2.connect(connection_string)
    
    async def store_message(self, message, user_id, conversation_id):
        # Store in PostgreSQL
        pass
```

3. **Use Real Abilities** from your application:
```python
from your_app.abilities import SpotifyAbility, CalendarAbility

assistant = BaseAssistant(llm=real_llm, memory=real_memory)
await assistant.register_ability(SpotifyAbility())
await assistant.register_ability(CalendarAbility())
```

## Testing Examples

Examples include self-verification. Look for output like:

```
✅ Assistant initialized!
✅ Registered 2 abilities
✅ Complete!
```

If you see `❌` errors, check:
1. Python version (3.8+ required)
2. bruno-core installation
3. Dependencies installed

## Next Steps

After running examples:

1. Read the [Creating Abilities Guide](../docs/guides/creating_abilities.md)
2. Explore [Custom LLM Guide](../docs/guides/custom_llm.md)
3. Check [Memory Backends Guide](../docs/guides/memory_backends.md)
4. Review [API Documentation](../docs/api/)

## Getting Help

If examples don't work:
1. Check requirements: `pip install -e .`
2. Verify Python version: `python --version`
3. See [Troubleshooting](../docs/troubleshooting.md)
4. Open an issue with error details
