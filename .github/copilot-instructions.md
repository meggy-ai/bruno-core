# Bruno Core - AI Coding Agent Instructions

## Project Overview
Bruno Core is the foundational package for the Bruno AI assistant ecosystem. It provides interfaces, base implementations, and utilities for building modular, extensible AI assistants with swappable components (LLM providers, memory backends, abilities).

**Architecture**: Interface-based plugin system with async-first design. Components register via Python entry points (`bruno.abilities`, `bruno.llm_providers`, `bruno.memory_backends` in pyproject.toml).

## Key Architectural Patterns

### 1. Interface-Based Design
All major components implement abstract interfaces from `bruno_core/interfaces/`:
- **AssistantInterface**: Main orchestrator (coordinates LLM, memory, abilities)
- **LLMInterface**: Language model providers
- **MemoryInterface**: Storage backends
- **AbilityInterface**: Executable actions (timers, notes, weather, etc.)

Base implementations live in `bruno_core/base/`. Always code against interfaces, not concrete implementations.

### 2. Plugin Registry System
Plugins discovered via `PluginRegistry` (see `bruno_core/registry/base.py`):
- Uses `importlib.metadata.entry_points()` to scan entry point groups
- Each registry validates plugins with `validate_plugin()` checking required methods
- Plugins registered by name and can be instantiated on-demand via `get_instance()`

**Example**: AbilityRegistry validates classes have `execute`, `get_metadata`, `can_handle` methods.

### 3. Pydantic Models for Type Safety
All data structures use Pydantic v2 (`bruno_core/models/`):
- **Message**: Conversation messages with `MessageRole` enum (system/user/assistant)
- **AbilityRequest/Response**: Structured ability execution
- **ConversationContext**: Session and user context management
- Models have validators (e.g., `Message.content_not_empty`) and JSON encoders for UUID/datetime

### 4. Async-First Event System
Event-driven architecture via `EventBus` (`bruno_core/events/bus.py`):
- Pub/sub pattern for decoupled components
- Event types in `EventType` enum
- Handlers registered with `subscribe()`, triggered with `publish()`

### 5. Custom Exception Hierarchy
All exceptions inherit from `BrunoError` (`bruno_core/utils/exceptions.py`):
- Structured with `message`, `details` dict, and `cause` chaining
- Specific types: `LLMError`, `MemoryError`, `AbilityError`, `RegistryError`, etc.
- Use appropriate exception types when raising errors

## Development Workflows

### Setup & Testing
```bash
# Install dev dependencies
pip install -e ".[dev,test,docs]"

# Run tests with coverage
pytest --cov=bruno_core --cov-report=term-missing

# Test specific module
pytest tests/unit/test_base.py

# Type checking
mypy bruno_core/

# Linting
ruff check bruno_core/
```

### Code Style Requirements
- **Black** formatting (line length: 100)
- **Google-style docstrings** with Args/Returns/Raises/Example sections
- **Type hints** required for all functions (`mypy` strict mode enabled)
- Use `structlog` for logging: `logger = get_logger(__name__)`
- Log events as structured data: `logger.info("event_name", key=value)`

### Documentation & Examples
- Generate docs: `mkdocs serve` (already running in terminal)
- Examples in `examples/` demonstrate real usage patterns
- See `examples/basic_assistant.py` for minimal setup, `examples/custom_ability.py` for plugin creation

## Critical Conventions

### Import Organization
Use relative imports within bruno_core, absolute for external:
```python
from bruno_core.interfaces.assistant import AssistantInterface
from bruno_core.models.message import Message, MessageRole
from bruno_core.utils.logging import get_logger
```

### Ability Creation Pattern
Abilities must implement three methods (see `AbilityInterface`):
1. `get_metadata()` → `AbilityMetadata` with name, description, parameters, examples
2. `execute(request: AbilityRequest)` → `AbilityResponse`
3. `can_handle(request)` → bool (optional filtering logic)

### Context Management
`BaseAssistant.process_message()` requires initialization via `await assistant.initialize()`. Always check `self.initialized` before processing.

### Testing Patterns
Use fixtures from `tests/conftest.py`:
- `MockLLM`: Predefined responses, tracks call count and last messages
- `MockMemory`: In-memory storage with conversation keying `{user_id}:{conversation_id}`
- `MockAbility`: Configurable success/failure responses

### Commit Conventions
Follow conventional commits:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation
- `test:` Test changes
- `refactor:` Code restructuring

## Entry Point Registration
When creating new abilities/providers, register in pyproject.toml:
```toml
[project.entry-points."bruno.abilities"]
my_ability = "my_package.abilities:MyAbility"
```

## Cross-Component Communication
- **Event Bus**: Decouple components with async events
- **Context Objects**: Pass `ConversationContext` through call chains
- **Registry Pattern**: Dynamic plugin discovery without hard dependencies

## Performance Considerations
- All I/O operations are async (LLM calls, memory storage, ability execution)
- `BaseAssistant` can execute multiple abilities concurrently
- Use `asyncio.gather()` for parallel operations

## Common Pitfalls
1. Don't forget `await assistant.initialize()` before processing messages
2. Always validate plugin classes implement required interface methods
3. Handle entry point discovery failures gracefully (multi-version Python compatibility)
4. Use structured logging, not print statements
5. Catch specific exception types, not bare `Exception` (unless re-raising)
