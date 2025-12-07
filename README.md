# meggy-ai
┌─────────────────────────────────────────┐
│         5. bruno-pa                     │  ← Applications (depends on everything)
│      (Personal Assistant)               │
└─────────────────────────────────────────┘
                  ▲
                  │ depends on
    ┌─────────────┼─────────────┬──────────┐
    │             │             │          │
┌───┴────┐  ┌────┴─────┐  ┌────┴────┐ ┌──┴─────────┐
│   3a.  │  │   3b.    │  │   3c.   │ │    4.      │
│ bruno- │  │  bruno-  │  │ bruno-  │ │  bruno-    │
│  llm   │  │  memory  │  │abilities│ │   docs     │
└────────┘  └──────────┘  └─────────┘ └────────────┘
    ▲            ▲             ▲            │
    │            │             │            │
    └────────────┴─────────────┴────────────┘
                  │ all depend on
            ┌─────┴──────┐
            │     1.     │
            │  bruno-    │  ← Foundation (no dependencies)
            │   core     │
            └────────────┘
                  ▲
                  │ (optional: start here)
            ┌─────┴──────┐
            │     2.     │
            │  bruno-    │  ← Examples & templates
            │ templates  │
            └────────────┘

bruno-llm/
├── clients/
│   ├── ollama.py      # Your local LLM
│   ├── claude.py      # Anthropic
│   └── openai.py      # OpenAI
├── factory.py         # LLMFactory
└── utils/
    └── token_counter.py

bruno-memory/
├── backends/
│   ├── sqlite.py      # Simple file-based
│   ├── redis.py       # Fast in-memory
│   └── postgres.py    # Production-grade
├── conversation_manager.py
├── context_compressor.py
└── memory_retriever.py

bruno-abilities/
├── timer/
│   └── timer_ability.py
├── alarm/
│   └── alarm_ability.py
├── notes/
│   └── notes_ability.py
└── weather/
    └── weather_ability.py

bruno-pa/
├── interfaces/
│   ├── voice/
│   │   └── main.py          # Your existing voice code
│   ├── text/
│   │   └── bruno_text.py    # Your existing text code
│   └── discord/
│       └── discord_bot.py   # Your existing Discord code
├── config/
│   └── settings.py
└── run.py                   # Entry point

# bruno-core
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

