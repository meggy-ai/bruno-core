# Architecture Overview

This document explains the design principles, architecture patterns, and component interactions in bruno-core.

## Design Principles

### 1. Modularity
- **Separation of Concerns**: Each component has a single, well-defined responsibility
- **Loose Coupling**: Components interact through interfaces, not concrete implementations
- **High Cohesion**: Related functionality is grouped together

### 2. Extensibility
- **Plugin Architecture**: New capabilities via entry points
- **Interface-Based Design**: Swap implementations without code changes
- **Base Class Templates**: Common functionality in reusable base classes

### 3. Type Safety
- **Pydantic Models**: Runtime validation and serialization
- **Type Hints**: Static type checking with mypy
- **Protocol Types**: Structural subtyping for flexibility

### 4. Async-First
- **Non-Blocking I/O**: All I/O operations are async
- **Concurrent Execution**: Parallel ability execution
- **Event-Driven**: Async event handlers

## System Architecture

### Layer Overview

```
┌──────────────────────────────────────────────────┐
│              Application Layer                    │
│         (Your AI Assistant Application)           │
└──────────────────────────────────────────────────┘
                      ▲
                      │ uses
┌──────────────────────────────────────────────────┐
│              Plugin Layer                         │
│    (Abilities, LLM Providers, Memory Backends)    │
└──────────────────────────────────────────────────┘
                      ▲
                      │ implements
┌──────────────────────────────────────────────────┐
│           Base Implementation Layer               │
│  (BaseAssistant, BaseAbility, ActionExecutor)    │
└──────────────────────────────────────────────────┘
                      ▲
                      │ uses
┌──────────────────────────────────────────────────┐
│              Interface Layer                      │
│   (Contracts: LLMInterface, MemoryInterface)     │
└──────────────────────────────────────────────────┘
                      ▲
                      │ depends on
┌──────────────────────────────────────────────────┐
│              Foundation Layer                     │
│    (Models, Utils, Registry, Events, Context)    │
└──────────────────────────────────────────────────┘
```

## Core Components

### 1. Interfaces (Contracts)

Interfaces define contracts that implementations must fulfill.

**Key Interfaces:**
- `AssistantInterface` - Main orchestrator
- `LLMInterface` - Language model provider
- `MemoryInterface` - Storage backend
- `AbilityInterface` - Ability/skill
- `EmbeddingInterface` - Vector embeddings

**Design Pattern**: Abstract Base Class (ABC)

```python
from abc import ABC, abstractmethod

class LLMInterface(ABC):
    @abstractmethod
    async def generate(self, messages, **kwargs) -> str:
        """Generate response from messages."""
        pass
```

### 2. Base Implementations

Reusable implementations that handle common patterns.

**BaseAssistant** - The main orchestrator:
```python
┌─────────────────────────────────────┐
│         BaseAssistant               │
├─────────────────────────────────────┤
│ - llm: LLMInterface                 │
│ - memory: MemoryInterface           │
│ - abilities: Dict[str, Ability]     │
├─────────────────────────────────────┤
│ + process_message()                 │
│ + register_ability()                │
│ + initialize()                      │
│ + shutdown()                        │
└─────────────────────────────────────┘
         │
         ├─► uses LLMInterface
         ├─► uses MemoryInterface
         └─► manages AbilityInterface
```

**ActionExecutor** - Orchestrates ability execution:
- Sequential or parallel execution
- Rollback on failure
- Result aggregation
- Statistics tracking

**ChainExecutor** - Sequential ability chains:
- Step-by-step execution
- Result passing between steps
- Conditional branching
- Error handling

### 3. Models (Data Structures)

Type-safe data models using Pydantic v2.

**Message Flow:**
```
User Input
    ↓
Message (role=USER, content=...)
    ↓
ConversationContext (messages=[...])
    ↓
LLM Processing
    ↓
AssistantResponse (text=..., actions=[...])
    ↓
Output to User
```

**Key Models:**
- `Message` - Chat messages with roles and metadata
- `ConversationContext` - Collection of messages with context
- `AssistantResponse` - Assistant's response with actions
- `AbilityRequest/Response` - Ability communication
- `MemoryEntry` - Stored memory with importance scoring

### 4. Registry System

Dynamic plugin discovery and management.

```
┌────────────────────────────────────┐
│       Plugin Registry              │
├────────────────────────────────────┤
│  Entry Points Discovery            │
│       ↓                            │
│  Plugin Validation                 │
│       ↓                            │
│  Instance Creation                 │
│       ↓                            │
│  Lifetime Management               │
└────────────────────────────────────┘
```

**Entry Point Format:**
```python
entry_points={
    "bruno.abilities": [
        "timer = my_package.abilities:TimerAbility",
    ]
}
```

**Usage:**
```python
registry = AbilityRegistry()
registry.discover_plugins()  # Auto-discover
timer = registry.get_instance("timer")
```

### 5. Context Management

Manages conversation state and history.

**ContextManager** - Rolling message windows:
- Fixed-size message buffer
- Automatic memory storage
- Compression triggers
- Multi-conversation support

**SessionManager** - Session lifecycle:
- Session creation/termination
- Activity tracking
- Timeout handling
- Statistics

**StateManager** - Persistent state:
- Key-value storage
- JSON serialization
- Namespace isolation
- File or in-memory storage

### 6. Event System

Pub/sub pattern for decoupled communication.

```
┌──────────────┐
│  Component A │
└──────────────┘
       │
       │ publish
       ↓
┌──────────────┐     subscribe      ┌──────────────┐
│  Event Bus   │ ─────────────────→ │  Component B │
└──────────────┘                     └──────────────┘
       │
       │ subscribe
       ↓
┌──────────────┐
│  Component C │
└──────────────┘
```

**Event Types:**
- Message events (received, sent, processed)
- Ability events (executing, executed, failed)
- Session events (started, ended)
- System events (started, stopped, health)

## Data Flow

### Message Processing Pipeline

```
1. User Input
      ↓
2. Create Message
      ↓
3. Add to Context
      ↓
4. Retrieve Relevant Memories
      ↓
5. Build LLM Context
      ↓
6. Generate LLM Response
      ↓
7. Detect Abilities
      ↓
8. Execute Abilities (if any)
      ↓
9. Create AssistantResponse
      ↓
10. Store in Memory
      ↓
11. Return Response
```

### Ability Execution Pipeline

```
1. Detect Ability Keywords
      ↓
2. Create AbilityRequest
      ↓
3. Validate Request
      ↓
4. Execute Action
      ↓
5. Handle Result/Error
      ↓
6. Create ActionResult
      ↓
7. Return to Assistant
```

## Design Patterns

### 1. Strategy Pattern
Swap algorithms at runtime (LLM providers, memory backends).

```python
# Different strategies
assistant = BaseAssistant(llm=OpenAIProvider(...))
assistant = BaseAssistant(llm=ClaudeProvider(...))
assistant = BaseAssistant(llm=OllamaProvider(...))
```

### 2. Template Method Pattern
Base classes define skeleton, subclasses implement specifics.

```python
class BaseAbility(AbilityInterface):
    async def execute(self, request):  # Template
        if not self.validate_request(request):
            return error_response()
        return await self.execute_action(request)  # Subclass implements
    
    @abstractmethod
    async def execute_action(self, request):  # To be implemented
        pass
```

### 3. Observer Pattern
Event system for loose coupling.

```python
bus.subscribe(EventType.MESSAGE_RECEIVED, log_handler)
bus.subscribe(EventType.MESSAGE_RECEIVED, metrics_handler)
bus.subscribe(EventType.MESSAGE_RECEIVED, analytics_handler)
```

### 4. Registry Pattern
Centralized plugin management.

```python
registry = AbilityRegistry()
registry.register("timer", TimerAbility)
timer = registry.get_instance("timer")
```

### 5. Facade Pattern
BaseAssistant provides simplified interface to complex subsystems.

```python
# Simple interface
response = await assistant.process_message(message, user_id, conv_id)

# Hides complexity of:
# - Context management
# - Memory retrieval
# - LLM interaction
# - Ability detection
# - Ability execution
# - Event publishing
```

## Extensibility Points

### 1. Custom LLM Providers
Implement `LLMInterface`:
```python
class CustomLLM(LLMInterface):
    async def generate(self, messages, **kwargs):
        # Your implementation
        pass
```

### 2. Custom Memory Backends
Implement `MemoryInterface`:
```python
class CustomMemory(MemoryInterface):
    async def store_message(self, message, user_id, conversation_id):
        # Your implementation
        pass
```

### 3. Custom Abilities
Extend `BaseAbility`:
```python
class WeatherAbility(BaseAbility):
    async def execute_action(self, request):
        # Your implementation
        pass
```

### 4. Event Handlers
Subscribe to events:
```python
class LoggingHandler(AsyncEventHandler):
    async def handle(self, event):
        # Your implementation
        pass
```

## Performance Considerations

### 1. Async Operations
All I/O is non-blocking:
```python
# Parallel execution
results = await asyncio.gather(
    llm.generate(messages),
    memory.retrieve_context(user_id, query),
    ability.execute(request)
)
```

### 2. Context Window Management
Rolling windows prevent unbounded growth:
```python
manager = ContextManager(max_messages=20)
# Automatically keeps only last 20 messages
```

### 3. Lazy Loading
Registry creates instances on-demand:
```python
# Plugin class loaded but not instantiated until needed
ability = registry.get_instance("timer")  # Created here
```

### 4. Event Bus Efficiency
Handlers execute concurrently:
```python
# All handlers run in parallel
await bus.publish(event)
```

## Security Considerations

### 1. Input Validation
All models validate input via Pydantic:
```python
message = Message(role=MessageRole.USER, content=user_input)
# Validated automatically
```

### 2. Sandboxed Execution
Abilities can't access other abilities' state:
```python
# Each ability is isolated
ability1 = registry.get_instance("timer")
ability2 = registry.get_instance("notes")
# No shared state
```

### 3. Permission System
Extend with custom permissions:
```python
class SecureAbility(BaseAbility):
    async def execute_action(self, request):
        if not self.check_permission(request.user_id):
            raise PermissionError()
        # Execute
```

## Testing Strategy

### 1. Unit Tests
Test individual components in isolation:
```python
# Mock dependencies
assistant = BaseAssistant(llm=MockLLM(), memory=MockMemory())
```

### 2. Integration Tests
Test component interactions:
```python
# Real implementations
assistant = BaseAssistant(llm=real_llm, memory=real_memory)
response = await assistant.process_message(...)
```

### 3. Mock Implementations
Provided in `tests/conftest.py`:
- `MockLLM` - Predictable LLM responses
- `MockMemory` - In-memory storage
- `MockAbility` - Test ability behavior

## Best Practices

### 1. Use Type Hints
```python
async def process(message: Message) -> AssistantResponse:
    ...
```

### 2. Handle Errors Gracefully
```python
try:
    response = await llm.generate(messages)
except Exception as e:
    logger.error("llm_failed", error=str(e))
    return error_response()
```

### 3. Log Structured Data
```python
logger.info("message_processed", user_id=user_id, duration=elapsed)
```

### 4. Use Context Managers
```python
async with assistant:
    response = await assistant.process_message(message)
```

### 5. Validate Early
```python
def validate_request(self, request: AbilityRequest) -> bool:
    # Fail fast
    if not request.parameters:
        return False
    return True
```

## Future Enhancements

Planned features:
- [ ] Streaming response support
- [ ] Distributed execution
- [ ] Plugin versioning & dependencies
- [ ] Hot reloading of abilities
- [ ] Enhanced observability
- [ ] Rate limiting & quotas
- [ ] Multi-modal support

---

For implementation details, see the [API Reference](api/).
