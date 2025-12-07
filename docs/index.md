# bruno-core Documentation

Welcome to **bruno-core** - a modular, extensible foundation for building AI assistants.

## Overview

bruno-core provides clean abstractions, swappable components, and a plugin architecture that enables you to build sophisticated conversational AI systems. It serves as the foundation layer that other Bruno packages build upon.

## Key Features

- 🧩 **Modular Architecture** - Clean separation between interfaces, implementations, and plugins
- 🔌 **Plugin System** - Easy registration via Python entry points
- 💬 **Conversation Management** - Context windows, sessions, and state persistence
- ⚡ **Async-First** - Built on asyncio for high-performance
- 🎯 **Action Execution** - Parallel execution, rollback, and chaining
- 📊 **Event System** - Pub/sub for decoupled communication
- 🧪 **Well Tested** - >80% code coverage
- 📝 **Type Safe** - Full type hints and Pydantic validation

## Quick Links

### Getting Started
- [Quick Start Guide](quickstart.md) - Get up and running in minutes
- [Architecture Overview](architecture.md) - Understand the system design
- [Installation](quickstart.md#installation) - Installation instructions

### API Reference
- [Interfaces](api/interfaces.md) - Abstract contracts
- [Base Classes](api/base.md) - Ready-to-extend implementations
- [Data Models](api/models.md) - Pydantic models

### Developer Guides
- [Creating Abilities](guides/creating_abilities.md) - Build custom abilities
- [Custom LLM Providers](guides/custom_llm.md) - Integrate any LLM
- [Memory Backends](guides/memory_backends.md) - Custom storage solutions

## Architecture

```
┌─────────────────────────────────────────┐
│         Your Application                │
└─────────────────────────────────────────┘
                  ▲
                  │ uses
    ┌─────────────┼─────────────┬──────────┐
    │             │             │          │
┌───┴────┐  ┌────┴─────┐  ┌────┴────┐ ┌──┴─────────┐
│ Custom │  │  Custom  │  │ Custom  │ │  Custom    │
│  LLM   │  │  Memory  │  │Abilities│ │  Events    │
└────────┘  └──────────┘  └─────────┘ └────────────┘
    ▲            ▲             ▲            ▲
    │            │             │            │
    └────────────┴─────────────┴────────────┘
                  │ implements
            ┌─────┴──────┐
            │  bruno-    │
            │   core     │
            └────────────┘
```

## Core Components

### Interfaces
Abstract contracts that define how components interact:
- `AssistantInterface` - Main orchestrator contract
- `LLMInterface` - Language model provider contract
- `MemoryInterface` - Storage backend contract
- `AbilityInterface` - Ability/skill contract
- `EmbeddingInterface` - Vector embedding contract

### Base Implementations
Ready-to-extend base classes:
- `BaseAssistant` - Default assistant implementation
- `BaseAbility` - Ability template with validation
- `ActionExecutor` - Action orchestration
- `ChainExecutor` - Sequential ability execution

### Models
Type-safe data structures:
- `Message` - Chat messages with roles
- `ConversationContext` - Message history
- `AbilityRequest/Response` - Ability communication
- `MemoryEntry` - Stored memories

### Registry
Plugin discovery and management:
- `AbilityRegistry` - Discover and load abilities
- `LLMProviderRegistry` - Manage LLM providers
- `MemoryBackendRegistry` - Manage storage backends

### Context Management
- `ContextManager` - Rolling message windows
- `SessionManager` - Session lifecycle
- `StateManager` - Persistent state storage

### Events
Pub/sub event system:
- `EventBus` - Event distribution
- `EventHandler` - Base event handlers
- Event types for all system activities

## Example Usage

```python
from bruno_core.base import BaseAssistant
from bruno_core.models import Message, MessageRole

# Initialize assistant
assistant = BaseAssistant(llm=your_llm, memory=your_memory)
await assistant.initialize()

# Process message
message = Message(role=MessageRole.USER, content="Hello!")
response = await assistant.process_message(
    message=message,
    user_id="user-123",
    conversation_id="conv-456"
)

print(response.text)
```

## Package Structure

```
bruno_core/
├── interfaces/      # Abstract contracts
├── base/           # Base implementations
├── models/         # Data models
├── registry/       # Plugin system
├── context/        # Context management
├── events/         # Event system
├── utils/          # Utilities
└── protocols/      # Type protocols
```

## Contributing

See our [Contributing Guide](../CONTRIBUTING.md) for development setup and guidelines.

## License

MIT License - see [LICENSE](../LICENSE) for details.

## Support

- [GitHub Issues](https://github.com/meggy-ai/bruno-core/issues)
- [GitHub Discussions](https://github.com/meggy-ai/bruno-core/discussions)
