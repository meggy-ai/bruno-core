# Bruno Core - Implementation Plan & Progress Tracker

## Project Overview
Transform the monolithic `old_code` implementation into a modular, extensible `bruno-core` package that serves as the foundation for the Bruno ecosystem. The core will provide interfaces, base implementations, and utilities that other packages (bruno-llm, bruno-memory, bruno-abilities, bruno-pa) will build upon.

---

## Task Status Legend
- 🔴 **NOT_STARTED** - Task not yet begun
- 🟡 **IN_PROGRESS** - Currently being worked on
- 🟢 **COMPLETED** - Task completed and verified
- ⚪ **BLOCKED** - Waiting on dependencies

---

## Phase 1: Foundation & Core Infrastructure 🔴 NOT_STARTED

### 1.1 Project Setup & Configuration 🔴 NOT_STARTED
**Status:** NOT_STARTED  
**Dependencies:** None  
**Estimated Time:** 2 hours

**Tasks:**
- [ ] Create `setup.py` with package metadata
- [ ] Create `pyproject.toml` for modern Python packaging
- [ ] Create `.gitignore` for Python projects
- [ ] Create `CHANGELOG.md` for version tracking
- [ ] Create `bruno_core/__init__.py` with version exports
- [ ] Create `bruno_core/__version__.py` with version info

**Reference Files:**
- None (new project setup)

**Deliverables:**
- Installable Python package structure
- Package configuration files
- Version management system

---

### 1.2 Data Models (Pydantic) 🔴 NOT_STARTED
**Status:** NOT_STARTED  
**Dependencies:** 1.1  
**Estimated Time:** 4 hours

**Tasks:**
- [ ] `bruno_core/models/__init__.py` - Package exports
- [ ] `bruno_core/models/message.py` - Message, Role, MessageType models
- [ ] `bruno_core/models/context.py` - ConversationContext, UserContext, SessionContext
- [ ] `bruno_core/models/response.py` - AssistantResponse, StreamResponse
- [ ] `bruno_core/models/memory.py` - MemoryEntry, MemoryMetadata, MemoryQuery
- [ ] `bruno_core/models/ability.py` - AbilityRequest, AbilityResponse, AbilityMetadata
- [ ] `bruno_core/models/config.py` - Configuration models

**Reference Files:**
- `old_code/core/bruno_interface.py` (BrunoAction, BrunoRequest, BrunoResponse)
- `old_code/memory/conversation_manager.py` (message structure)
- `old_code/memory/memory_store.py` (memory data structures)

**Key Decisions:**
- Use Pydantic v2 for validation
- All models immutable by default (frozen=True where appropriate)
- Include JSON serialization methods
- Add comprehensive docstrings

**Deliverables:**
- Type-safe data models with validation
- Consistent data structures across ecosystem
- JSON serialization support

---

### 1.3 Utility Modules 🔴 NOT_STARTED
**Status:** NOT_STARTED  
**Dependencies:** 1.1  
**Estimated Time:** 3 hours

**Tasks:**
- [ ] `bruno_core/utils/__init__.py` - Package exports
- [ ] `bruno_core/utils/exceptions.py` - Custom exception hierarchy
- [ ] `bruno_core/utils/logging.py` - Structured logging setup
- [ ] `bruno_core/utils/validation.py` - Input validation helpers
- [ ] `bruno_core/utils/async_utils.py` - Async/await utilities
- [ ] `bruno_core/utils/text_processing.py` - Text manipulation utilities
- [ ] `bruno_core/utils/config.py` - Configuration loading/management

**Reference Files:**
- `old_code/utils/config.py` (BrunoConfig)
- `old_code/utils/permissions.py` (permission checks)

**Key Decisions:**
- Use structlog for structured logging
- Create exception hierarchy (BrunoError base class)
- Support both YAML and JSON config files
- Environment variable overrides

**Deliverables:**
- Reusable utility functions
- Consistent error handling
- Configuration management system

---

## Phase 2: Core Interfaces (Contracts) 🔴 NOT_STARTED

### 2.1 Base Interfaces 🔴 NOT_STARTED
**Status:** NOT_STARTED  
**Dependencies:** 1.2, 1.3  
**Estimated Time:** 4 hours

**Tasks:**
- [ ] `bruno_core/interfaces/__init__.py` - Interface exports
- [ ] `bruno_core/interfaces/assistant.py` - AssistantInterface (main orchestrator)
- [ ] `bruno_core/interfaces/llm.py` - LLMInterface (text generation)
- [ ] `bruno_core/interfaces/memory.py` - MemoryInterface (storage & retrieval)
- [ ] `bruno_core/interfaces/ability.py` - AbilityInterface (executable actions)
- [ ] `bruno_core/interfaces/embedding.py` - EmbeddingInterface (vector embeddings)
- [ ] `bruno_core/interfaces/stream.py` - StreamInterface (streaming responses)

**Reference Files:**
- `old_code/llm/base.py` (BaseLLMClient)
- `old_code/core/base_assistant.py` (BaseBrunoAssistant)
- `old_code/memory/memory_store.py` (database operations)

**Key Interface Methods:**

**AssistantInterface:**
```python
- async def process_message(request: BrunoRequest) -> BrunoResponse
- async def register_ability(ability: AbilityInterface) -> None
- async def shutdown() -> None
```

**LLMInterface:**
```python
- async def generate(messages: List[Message], **kwargs) -> str
- async def stream(messages: List[Message], **kwargs) -> AsyncIterator[str]
- def get_token_count(text: str) -> int
```

**MemoryInterface:**
```python
- async def store_message(message: Message) -> None
- async def retrieve_context(query: str, limit: int) -> List[Message]
- async def search_memories(query: str) -> List[MemoryEntry]
```

**AbilityInterface:**
```python
- async def execute(request: AbilityRequest) -> AbilityResponse
- def get_metadata() -> AbilityMetadata
- def can_handle(request: AbilityRequest) -> bool
```

**Deliverables:**
- Abstract base classes defining all contracts
- Comprehensive docstrings
- Type hints for all methods

---

### 2.2 Protocol Definitions 🔴 NOT_STARTED
**Status:** NOT_STARTED  
**Dependencies:** 2.1  
**Estimated Time:** 2 hours

**Tasks:**
- [ ] `bruno_core/protocols/__init__.py` - Protocol exports
- [ ] `bruno_core/protocols/interfaces.py` - Runtime-checkable protocols

**Key Decisions:**
- Use typing.Protocol for structural subtyping
- Make protocols runtime-checkable
- Support duck typing for flexibility

**Deliverables:**
- Alternative to ABC inheritance
- Duck typing support
- Runtime type checking

---

## Phase 3: Base Implementations 🔴 NOT_STARTED

### 3.1 Base Assistant 🔴 NOT_STARTED
**Status:** NOT_STARTED  
**Dependencies:** 2.1, 1.2  
**Estimated Time:** 6 hours

**Tasks:**
- [ ] `bruno_core/base/__init__.py` - Base class exports
- [ ] `bruno_core/base/assistant.py` - BaseAssistant implementation
- [ ] Implement message processing pipeline
- [ ] Implement ability registration & discovery
- [ ] Implement context management
- [ ] Implement error handling & recovery
- [ ] Add lifecycle hooks (on_start, on_shutdown, etc.)

**Reference Files:**
- `old_code/core/base_assistant.py` (BaseBrunoAssistant)
- `old_code/core/bruno_interface.py` (BrunoInterface)

**Key Features:**
- Async-first design
- Plugin architecture for abilities
- Middleware support for request/response
- Event emission for monitoring
- Graceful shutdown handling

**Deliverables:**
- Fully functional BaseAssistant class
- Ability to process messages end-to-end
- Plugin registration system

---

### 3.2 Action Executor 🔴 NOT_STARTED
**Status:** NOT_STARTED  
**Dependencies:** 2.1, 1.2  
**Estimated Time:** 3 hours

**Tasks:**
- [ ] `bruno_core/base/executor.py` - ActionExecutor implementation
- [ ] Implement action queue management
- [ ] Implement parallel action execution
- [ ] Implement action result aggregation
- [ ] Add rollback support for failed actions
- [ ] Add action logging & auditing

**Reference Files:**
- `old_code/core/action_executor.py` (ActionExecutor)

**Key Features:**
- Execute actions in sequence or parallel
- Handle action dependencies
- Rollback on failure
- Action result collection

**Deliverables:**
- ActionExecutor class
- Action execution pipeline
- Error recovery mechanisms

---

### 3.3 Base Ability 🔴 NOT_STARTED
**Status:** NOT_STARTED  
**Dependencies:** 2.1, 1.2  
**Estimated Time:** 2 hours

**Tasks:**
- [ ] `bruno_core/base/ability.py` - BaseAbility implementation
- [ ] Implement ability lifecycle methods
- [ ] Implement validation logic
- [ ] Implement metadata management
- [ ] Add ability composition support

**Reference Files:**
- `old_code/abilities/conversation_ability.py`
- `old_code/abilities/timer_manager.py`
- `old_code/abilities/music_manager.py`

**Key Features:**
- Standard lifecycle (init, execute, cleanup)
- Input validation
- Metadata for discovery
- Composable abilities

**Deliverables:**
- BaseAbility class
- Ability template for extensions
- Validation framework

---

### 3.4 Chain Executor 🔴 NOT_STARTED
**Status:** NOT_STARTED  
**Dependencies:** 3.2, 3.3  
**Estimated Time:** 3 hours

**Tasks:**
- [ ] `bruno_core/base/chain.py` - ChainExecutor implementation
- [ ] Implement sequential ability chaining
- [ ] Implement conditional branching
- [ ] Implement result passing between abilities
- [ ] Add chain visualization/debugging

**Reference Files:**
- `old_code/core/action_executor.py` (multi-action execution)

**Key Features:**
- Execute abilities in sequence
- Pass output of one ability to next
- Conditional execution
- Error handling in chains

**Deliverables:**
- ChainExecutor class
- Workflow orchestration
- Chain debugging tools

---

## Phase 4: Plugin Registry System 🔴 NOT_STARTED

### 4.1 Registry Infrastructure 🔴 NOT_STARTED
**Status:** NOT_STARTED  
**Dependencies:** 2.1, 3.3  
**Estimated Time:** 4 hours

**Tasks:**
- [ ] `bruno_core/registry/__init__.py` - Registry exports
- [ ] `bruno_core/registry/ability_registry.py` - Ability plugin registry
- [ ] `bruno_core/registry/llm_registry.py` - LLM provider registry
- [ ] `bruno_core/registry/memory_registry.py` - Memory backend registry
- [ ] Implement plugin discovery mechanism
- [ ] Implement plugin versioning
- [ ] Implement dependency resolution

**Key Features:**
- Automatic plugin discovery via entry points
- Manual registration support
- Plugin validation
- Dependency management
- Version compatibility checking

**Deliverables:**
- Plugin registry system
- Discovery mechanism
- Version management

---

## Phase 5: Context Management 🔴 NOT_STARTED

### 5.1 Context Managers 🔴 NOT_STARTED
**Status:** NOT_STARTED  
**Dependencies:** 1.2, 2.1  
**Estimated Time:** 4 hours

**Tasks:**
- [ ] `bruno_core/context/__init__.py` - Context exports
- [ ] `bruno_core/context/manager.py` - ContextManager implementation
- [ ] `bruno_core/context/session.py` - SessionManager implementation
- [ ] `bruno_core/context/state.py` - StateManager implementation
- [ ] Implement context window management
- [ ] Implement state persistence
- [ ] Implement session lifecycle

**Reference Files:**
- `old_code/memory/conversation_manager.py` (ConversationManager)

**Key Features:**
- Rolling context window
- Session state management
- Context compression triggers
- Multi-user support

**Deliverables:**
- ContextManager class
- SessionManager class
- StateManager class

---

## Phase 6: Event System 🔴 NOT_STARTED

### 6.1 Event Bus & Handlers 🔴 NOT_STARTED
**Status:** NOT_STARTED  
**Dependencies:** 1.2, 1.3  
**Estimated Time:** 3 hours

**Tasks:**
- [ ] `bruno_core/events/__init__.py` - Event exports
- [ ] `bruno_core/events/bus.py` - EventBus implementation
- [ ] `bruno_core/events/handlers.py` - Event handler base classes
- [ ] `bruno_core/events/types.py` - Event type definitions
- [ ] Implement pub/sub mechanism
- [ ] Implement event filtering
- [ ] Implement async event handling

**Key Features:**
- Publish/subscribe pattern
- Async event handlers
- Event filtering & routing
- Event history/replay

**Deliverables:**
- EventBus class
- Event handler framework
- Event type definitions

---

## Phase 7: Testing Infrastructure 🔴 NOT_STARTED

### 7.1 Unit Tests 🔴 NOT_STARTED
**Status:** NOT_STARTED  
**Dependencies:** All previous phases  
**Estimated Time:** 8 hours

**Tasks:**
- [ ] `tests/conftest.py` - Pytest fixtures & configuration
- [ ] `tests/unit/test_base_assistant.py` - BaseAssistant tests
- [ ] `tests/unit/test_executor.py` - ActionExecutor tests
- [ ] `tests/unit/test_registry.py` - Registry tests
- [ ] `tests/unit/test_context.py` - Context management tests
- [ ] `tests/unit/test_models.py` - Data model tests
- [ ] `tests/unit/test_utils.py` - Utility tests
- [ ] `tests/fixtures/sample_data.py` - Test data fixtures

**Key Coverage:**
- Unit tests for all core classes
- Mock LLM, Memory, Abilities
- Edge case testing
- Error handling validation

**Deliverables:**
- Comprehensive unit test suite
- Mock implementations for testing
- Test fixtures & helpers
- >80% code coverage

---

### 7.2 Integration Tests 🔴 NOT_STARTED
**Status:** NOT_STARTED  
**Dependencies:** 7.1  
**Estimated Time:** 4 hours

**Tasks:**
- [ ] `tests/integration/test_full_flow.py` - End-to-end tests
- [ ] `tests/integration/test_ability_execution.py` - Ability integration
- [ ] `tests/integration/test_plugin_system.py` - Plugin loading tests
- [ ] Test complete message processing pipeline
- [ ] Test ability chaining
- [ ] Test error recovery

**Deliverables:**
- Integration test suite
- End-to-end workflow validation
- Plugin integration tests

---

## Phase 8: Documentation 🔴 NOT_STARTED

### 8.1 API Documentation 🔴 NOT_STARTED
**Status:** NOT_STARTED  
**Dependencies:** All implementation phases  
**Estimated Time:** 6 hours

**Tasks:**
- [ ] `docs/index.md` - Main documentation entry
- [ ] `docs/quickstart.md` - Quick start guide
- [ ] `docs/architecture.md` - Architecture overview
- [ ] `docs/api/interfaces.md` - Interface documentation
- [ ] `docs/api/base.md` - Base class documentation
- [ ] `docs/api/models.md` - Data model documentation
- [ ] `docs/guides/creating_abilities.md` - Ability creation guide
- [ ] `docs/guides/custom_llm.md` - LLM provider guide
- [ ] `docs/guides/memory_backends.md` - Memory backend guide

**Deliverables:**
- Complete API documentation
- User guides & tutorials
- Architecture documentation

---

### 8.2 Examples 🔴 NOT_STARTED
**Status:** NOT_STARTED  
**Dependencies:** All implementation phases  
**Estimated Time:** 4 hours

**Tasks:**
- [ ] `examples/basic_assistant.py` - Basic usage example
- [ ] `examples/custom_ability.py` - Custom ability example
- [ ] `examples/custom_llm.py` - Custom LLM provider example
- [ ] `examples/memory_usage.py` - Memory system example
- [ ] `examples/event_handling.py` - Event system example
- [ ] Add inline documentation to examples

**Deliverables:**
- Working example scripts
- Commented code examples
- Usage patterns demonstration

---

## Phase 9: CI/CD & Release 🔴 NOT_STARTED

### 9.1 GitHub Actions Setup 🔴 NOT_STARTED
**Status:** NOT_STARTED  
**Dependencies:** 7.1, 7.2  
**Estimated Time:** 3 hours

**Tasks:**
- [ ] `.github/workflows/ci.yml` - Continuous integration
- [ ] `.github/workflows/publish.yml` - PyPI publishing
- [ ] `.github/workflows/docs.yml` - Documentation deployment
- [ ] Configure automated testing
- [ ] Configure code quality checks
- [ ] Configure security scanning

**Deliverables:**
- Automated CI/CD pipeline
- Automated testing on PR
- Automated publishing

---

### 9.2 Package Release 🔴 NOT_STARTED
**Status:** NOT_STARTED  
**Dependencies:** 9.1, 8.1  
**Estimated Time:** 2 hours

**Tasks:**
- [ ] Create release checklist
- [ ] Version tagging strategy
- [ ] PyPI package preparation
- [ ] Release notes generation
- [ ] Initial v0.1.0 release

**Deliverables:**
- Published package on PyPI
- Release documentation
- Versioning strategy

---

## Progress Summary

### Overall Progress: 0% Complete

| Phase | Status | Progress | Estimated Time |
|-------|--------|----------|----------------|
| Phase 1: Foundation | 🔴 NOT_STARTED | 0/3 tasks | 9 hours |
| Phase 2: Interfaces | 🔴 NOT_STARTED | 0/2 tasks | 6 hours |
| Phase 3: Base Implementations | 🔴 NOT_STARTED | 0/4 tasks | 14 hours |
| Phase 4: Registry | 🔴 NOT_STARTED | 0/1 tasks | 4 hours |
| Phase 5: Context | 🔴 NOT_STARTED | 0/1 tasks | 4 hours |
| Phase 6: Events | 🔴 NOT_STARTED | 0/1 tasks | 3 hours |
| Phase 7: Testing | 🔴 NOT_STARTED | 0/2 tasks | 12 hours |
| Phase 8: Documentation | 🔴 NOT_STARTED | 0/2 tasks | 10 hours |
| Phase 9: CI/CD | 🔴 NOT_STARTED | 0/2 tasks | 5 hours |
| **TOTAL** | | **0/18 tasks** | **67 hours** |

---

## Task Tracking Instructions

### How to Update This Document

1. **Starting a task:**
   - Change status from 🔴 NOT_STARTED to 🟡 IN_PROGRESS
   - Add current date in "Started: YYYY-MM-DD"

2. **Completing a task:**
   - Change status from 🟡 IN_PROGRESS to 🟢 COMPLETED
   - Check off all sub-tasks
   - Add completion date: "Completed: YYYY-MM-DD"
   - Update progress percentage

3. **Blocking a task:**
   - Change status to ⚪ BLOCKED
   - Add "Blocked by: [reason]"

4. **Progress updates:**
   - Update the Progress Summary table after each task
   - Recalculate overall percentage

### Example Task Update:
```markdown
### 1.1 Project Setup & Configuration 🟢 COMPLETED
**Status:** COMPLETED  
**Started:** 2025-12-07  
**Completed:** 2025-12-07  
**Dependencies:** None  
**Estimated Time:** 2 hours  
**Actual Time:** 1.5 hours

**Tasks:**
- [x] Create `setup.py` with package metadata
- [x] Create `pyproject.toml` for modern Python packaging
...
```

---

## Key Architectural Decisions

### 1. **Async-First Design**
- All I/O operations are async
- Use `asyncio` for concurrency
- Support both sync and async ability execution

### 2. **Plugin Architecture**
- Use Python entry points for discovery
- Manual registration also supported
- Interface-based contracts

### 3. **Type Safety**
- Pydantic v2 for data validation
- Type hints throughout
- Runtime type checking where needed

### 4. **Separation of Concerns**
- bruno-core: Interfaces & base implementations
- bruno-llm: LLM provider implementations
- bruno-memory: Memory backend implementations
- bruno-abilities: Ability implementations
- bruno-pa: Personal assistant application

### 5. **Testing Strategy**
- Mock implementations for testing
- Unit tests for individual components
- Integration tests for workflows
- 80%+ code coverage target

### 6. **Configuration Management**
- YAML/JSON config files
- Environment variable overrides
- Pydantic models for validation

---

## Dependencies & Prerequisites

### Required Python Packages
```toml
[dependencies]
pydantic = "^2.0"
typing-extensions = "^4.0"
python-dotenv = "^1.0"
structlog = "^24.0"
```

### Development Dependencies
```toml
[dev-dependencies]
pytest = "^7.0"
pytest-asyncio = "^0.21"
pytest-cov = "^4.0"
black = "^23.0"
mypy = "^1.0"
ruff = "^0.1"
```

---

## Migration Path from old_code

### Components to Extract:

1. **LLM Interface** ← `old_code/llm/base.py`
2. **Assistant Base** ← `old_code/core/base_assistant.py`
3. **Action Executor** ← `old_code/core/action_executor.py`
4. **Bruno Interface** ← `old_code/core/bruno_interface.py`
5. **Memory Interface** ← `old_code/memory/memory_store.py`
6. **Conversation Manager** ← `old_code/memory/conversation_manager.py`
7. **Ability Pattern** ← `old_code/abilities/*_manager.py`

### Transformation Strategy:
1. Extract interfaces from concrete implementations
2. Separate concerns into distinct modules
3. Replace tight coupling with dependency injection
4. Convert sync code to async where beneficial
5. Add comprehensive type hints
6. Create Pydantic models from dict structures

---

## Notes & Considerations

### Critical Design Principles:
- **Loose Coupling**: Components communicate via interfaces
- **High Cohesion**: Related functionality grouped together
- **Open/Closed**: Open for extension, closed for modification
- **Dependency Inversion**: Depend on abstractions, not concretions

### Testing Philosophy:
- Write tests alongside implementation
- Mock external dependencies
- Test error paths, not just happy paths
- Integration tests for critical workflows

### Documentation Standards:
- Comprehensive docstrings (Google style)
- Type hints on all public APIs
- Examples in documentation
- Architecture decision records (ADRs)

---

## Revision History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-12-07 | 1.0 | Initial plan created | GitHub Copilot |

---

**Last Updated:** 2025-12-07  
**Plan Version:** 1.0  
**Overall Status:** 🔴 NOT_STARTED (0%)
