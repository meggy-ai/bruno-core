# bruno-core

BELLOW IS THE NEW ARCHITECTURE
```
bruno core

Bruno Core Package Structure
=============================

This outlines the complete structure and organization of bruno-core,
the foundational package for the Bruno ecosystem.

Directory Structure:
--------------------

bruno-core/
├── setup.py
├── pyproject.toml
├── README.md
├── LICENSE
├── CHANGELOG.md
├── .gitignore
├── .pre-commit-config.yaml
├── bruno_core/
│   ├── __init__.py
│   ├── __version__.py
│   │
│   ├── interfaces/              # Abstract Base Classes (Contracts)
│   │   ├── __init__.py
│   │   ├── assistant.py         # AssistantInterface
│   │   ├── llm.py              # LLMInterface
│   │   ├── memory.py           # MemoryInterface
│   │   ├── ability.py          # AbilityInterface
│   │   ├── embedding.py        # EmbeddingInterface
│   │   └── stream.py           # StreamInterface
│   │
│   ├── base/                    # Base Implementations
│   │   ├── __init__.py
│   │   ├── assistant.py         # BaseAssistant (main orchestrator)
│   │   ├── executor.py          # ActionExecutor
│   │   ├── ability.py           # BaseAbility
│   │   └── chain.py             # ChainExecutor (for complex workflows)
│   │
│   ├── models/                  # Data Models (Pydantic)
│   │   ├── __init__.py
│   │   ├── message.py           # Message, Role, MessageType
│   │   ├── context.py           # ConversationContext, UserContext
│   │   ├── response.py          # AssistantResponse
│   │   ├── memory.py            # MemoryEntry, MemoryMetadata
│   │   ├── ability.py           # AbilityRequest, AbilityResponse
│   │   └── config.py            # Configuration models
│   │
│   ├── registry/                # Plugin Registry System
│   │   ├── __init__.py
│   │   ├── ability_registry.py  # Ability plugin registry
│   │   ├── llm_registry.py      # LLM provider registry
│   │   └── memory_registry.py   # Memory backend registry
│   │
│   ├── context/                 # Context Management
│   │   ├── __init__.py
│   │   ├── manager.py           # ContextManager
│   │   ├── session.py           # SessionManager
│   │   └── state.py             # StateManager
│   │
│   ├── utils/                   # Utilities
│   │   ├── __init__.py
│   │   ├── logging.py           # Structured logging setup
│   │   ├── config.py            # Configuration loading
│   │   ├── exceptions.py        # Custom exceptions
│   │   ├── validation.py        # Input validation
│   │   ├── async_utils.py       # Async helpers
│   │   └── text_processing.py   # Text utilities
│   │
│   ├── events/                  # Event System
│   │   ├── __init__.py
│   │   ├── bus.py              # EventBus
│   │   ├── handlers.py         # Event handlers
│   │   └── types.py            # Event types
│   │
│   └── protocols/               # Type Protocols (Python 3.8+)
│       ├── __init__.py
│       └── interfaces.py        # Runtime checkable protocols
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── unit/
│   │   ├── test_base_assistant.py
│   │   ├── test_executor.py
│   │   ├── test_registry.py
│   │   └── test_context.py
│   ├── integration/
│   │   ├── test_full_flow.py
│   │   └── test_ability_execution.py
│   └── fixtures/
│       └── sample_data.py
│
├── examples/
│   ├── basic_assistant.py
│   ├── custom_ability.py
│   ├── custom_llm.py
│   └── memory_usage.py
│
├── docs/
│   ├── index.md
│   ├── quickstart.md
│   ├── architecture.md
│   ├── api/
│   │   ├── interfaces.md
│   │   ├── base.md
│   │   └── models.md
│   └── guides/
│       ├── creating_abilities.md
│       ├── custom_llm.md
│       └── memory_backends.md
│
└── .github/
    └── workflows/
        ├── ci.yml
        ├── publish.yml
        └── docs.yml
"""

```
We have our existing implementation in root_dir/old_code, am tryint to redesign the architecture for the old code by separting the code base in different repos with different responsibilities.

Think of bruno-core as the rulebook or blueprint for the entire Bruno ecosystem.
Simple Analogy: Building Blocks

```
bruno-core = The LEGO baseplate + instruction manual

You define:
- What pieces exist (LLM, Memory, Abilities)
- How pieces connect together
- Rules pieces must follow

Other packages = The actual LEGO pieces

They implement:
- Specific LLM providers (Claude, GPT, Ollama)
- Specific memory backends (SQLite, Redis, Postgres)
- Specific abilities (Timer, Alarm, Notes)

bruno-pa = The finished LEGO model

It assembles:
- Picks which pieces to use
- Connects them together
- Creates the final product
```

Why Does bruno-core Exist?

Problems:

❌ Want to use Claude instead of Ollama? → Rewrite everything
❌ Want Redis instead of SQLite? → Rewrite everything
❌ Want to add weather ability? → Modify core code
❌ Want to build AI Friend using same LLM? → Copy-paste code
❌ Want to test? → Need real APIs, databases, etc.

Solution With bruno-core:
Now you can:

✅ Swap Ollama → Claude: Just change one line
✅ Swap SQLite → Redis: Just change one line
✅ Add weather: Just register new ability
✅ Build AI Friend: Reuse same foundation
✅ Test: Use mock LLM, mock memory (no real APIs needed)

What bruno-core Contains
1. Interfaces (The Rules)
These are contracts - promises that implementations must keep.

# bruno_core/interfaces/llm.py

class LLMInterface(ABC):
    """Every LLM provider MUST implement these methods"""
    
    @abstractmethod
    async def generate(self, messages, temperature, max_tokens):
        """Generate a response - EVERY LLM must do this"""
        pass
    
    @abstractmethod
    async def stream(self, messages):
        """Stream tokens - EVERY LLM must support this"""
        pass

Why this matters:

# bruno-llm implements this for Claude
class ClaudeClient(LLMInterface):
    async def generate(self, messages, temperature, max_tokens):
        # Claude-specific code
        return self.anthropic.messages.create(...)

# bruno-llm implements this for Ollama
class OllamaClient(LLMInterface):
    async def generate(self, messages, temperature, max_tokens):
        # Ollama-specific code
        return requests.post("http://localhost:11434", ...)

# bruno-pa doesn't care which one you use!
llm = ClaudeClient()  # or OllamaClient() - works the same!

Models (The Data Structures)
These define what data looks like across the entire system.

# bruno_core/models/message.py

class Message:
    """A message in a conversation"""
    role: str  # "user" or "assistant"
    content: str  # The actual text
    timestamp: datetime
    metadata: dict

class ConversationContext:
    """All the context for a conversation"""
    user_id: str
    messages: List[Message]
    user_data: dict  # User preferences, history, etc.

Why this matters:

Everyone speaks the same language
Pass data between components easily
Type checking catches errors early

3. Base Classes (The Foundation)
These provide default implementations that you can extend.

Why this matters:

Don't reinvent the wheel
Focus on customization, not boilerplate
Consistent behavior across applications

4. Registry (The Plugin System)
This allows dynamic discovery of abilities.

5. Utils (Common Tools)
Shared utilities everyone needs.

Without bruno-core (Tightly Coupled) old_code codebase is tightly coupled

Problems:

Can't use Claude instead of Ollama without rewriting
Can't add new abilities without modifying core code
Can't test without real Whisper, Piper, Ollama
Can't reuse this code for AI Friend (too specific)

With bruno-core (Loosely Coupled):

Benefits:

✅ Swap Claude ↔ Ollama: Change one line
✅ Add new ability: Register it, done
✅ Test: Use MockLLM, MockMemory
✅ Reuse for AI Friend: Same foundation, different app

Why This Architecture is Powerful
1. Swappable Components
2. Easy Testing
3. Community Extensions
Others can build plugins:

4. Multiple Applications

# Personal Assistant
from bruno_core import BaseAssistant
assistant = BaseAssistant(llm, memory, [TimerAbility(), WeatherAbility()])

# AI Friend (different personality, different abilities)
from bruno_core import BaseAssistant
friend = BaseAssistant(llm, memory, [EmotionAbility(), StoryAbility()])

# AI Tutor (educational focus)
from bruno_core import BaseAssistant
tutor = BaseAssistant(llm, memory, [QuizAbility(), ExplainAbility()])


So and so forth

