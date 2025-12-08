# Bruno Core

Hello

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue)](http://mypy-lang.org/)

**Bruno Core** is the foundational package for the Bruno AI assistant ecosystem. It provides a modular, extensible framework for building AI assistants with swappable components through a plugin-based architecture.

## 🎯 Key Features

- **🔌 Plugin Architecture**: Dynamically load LLM providers, memory backends, and abilities via Python entry points
- **🎭 Interface-Based Design**: Code against interfaces, not implementations - swap components without changing code
- **🛡️ Type Safety**: Full Pydantic v2 models with strict mypy type checking
- **⚡ Async-First**: Non-blocking I/O for all operations with concurrent ability execution
- **📡 Event-Driven**: Decoupled components communicate via async event bus
- **📝 Structured Logging**: Built-in structured logging with structlog
- **🎨 Extensible**: Create custom abilities, LLM providers, and memory backends

## 🏗️ Architecture

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

## 🚀 Quick Start

### Installation

```bash
pip install bruno-core
```

### Basic Usage

```python
import asyncio
from bruno_core.base import BaseAssistant
from bruno_core.models import Message, MessageRole

# Import your LLM and Memory implementations
from my_llm import MyLLM
from my_memory import MyMemory

async def main():
    # Initialize components
    llm = MyLLM(api_key="your-api-key")
    memory = MyMemory()

    # Create assistant
    assistant = BaseAssistant(llm=llm, memory=memory)
    await assistant.initialize()

    # Process message
    message = Message(role=MessageRole.USER, content="Hello, Bruno!")
    response = await assistant.process_message(message)

    print(response.text)

asyncio.run(main())
```

## 📦 Core Components

### Interfaces
Define contracts for pluggable components:
- **`AssistantInterface`**: Main orchestrator
- **`LLMInterface`**: Language model providers
- **`MemoryInterface`**: Storage backends
- **`AbilityInterface`**: Executable actions

### Base Implementations
Ready-to-use implementations:
- **`BaseAssistant`**: Coordinates LLM, memory, and abilities
- **`BaseAbility`**: Template for creating custom abilities
- **`ActionExecutor`**: Manages concurrent ability execution

### Models (Pydantic v2)
Type-safe data structures:
- **`Message`**: Conversation messages with roles
- **`ConversationContext`**: Session and user context
- **`AbilityRequest/Response`**: Structured ability I/O

### Plugin Registry
Dynamic component discovery:
- Scan entry points: `bruno.abilities`, `bruno.llm_providers`, `bruno.memory_backends`
- Validate plugin classes
- Lazy instantiation

## 🔌 Creating a Custom Ability

```python
from bruno_core.base import BaseAbility
from bruno_core.models import AbilityMetadata, AbilityRequest, AbilityResponse

class CalculatorAbility(BaseAbility):
    def get_metadata(self) -> AbilityMetadata:
        return AbilityMetadata(
            name="calculator",
            description="Perform basic math operations",
            parameters=[...],
            examples=["Calculate 5 + 3"]
        )

    async def execute_action(self, request: AbilityRequest) -> AbilityResponse:
        operation = request.parameters["operation"]
        result = eval(f"{request.parameters['a']} {operation} {request.parameters['b']}")

        return AbilityResponse(
            request_id=request.id,
            ability_name="calculator",
            success=True,
            data={"result": result}
        )
```

Register in `pyproject.toml`:
```toml
[project.entry-points."bruno.abilities"]
calculator = "my_package.abilities:CalculatorAbility"
```

## 🛠️ Development

### Setup

```bash
# Clone repository
git clone https://github.com/meggy-ai/bruno-core.git
cd bruno-core

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dev dependencies
pip install -e ".[dev,test,docs]"

# Install pre-commit hooks
pre-commit install
```

### Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=bruno_core --cov-report=term-missing

# Specific test file
pytest tests/unit/test_base.py
```

### Code Quality

```bash
# Format code
black bruno_core/ tests/ examples/

# Type checking
mypy bruno_core/

# Linting
ruff check bruno_core/
```

Pre-commit hooks automatically run formatting, linting, and type checking.

## 📚 Documentation

- **[Full Documentation](https://meggy-ai.github.io/bruno-core/)**
- **[Quick Start Guide](https://meggy-ai.github.io/bruno-core/quickstart/)**
- **[Architecture Overview](https://meggy-ai.github.io/bruno-core/architecture/)**
- **[API Reference](https://meggy-ai.github.io/bruno-core/api/)**

### Local Documentation

```bash
# Serve docs locally
mkdocs serve

# Build static site
mkdocs build
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Commit Conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Test changes
- `refactor:` Code restructuring

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Related Projects

- **bruno-llm**: LLM provider implementations (OpenAI, Claude, Ollama)
- **bruno-memory**: Memory backend implementations (SQLite, Redis, PostgreSQL)
- **bruno-abilities**: Pre-built abilities (timers, notes, weather)
- **bruno-pa**: Personal assistant application

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/meggy-ai/bruno-core/issues)
- **Discussions**: [GitHub Discussions](https://github.com/meggy-ai/bruno-core/discussions)
- **Documentation**: [https://meggy-ai.github.io/bruno-core/](https://meggy-ai.github.io/bruno-core/)

---

Made with ❤️ by the Meggy AI team
