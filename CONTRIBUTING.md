# Contributing to Bruno Core

Thank you for your interest in contributing to Bruno Core! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful and inclusive. We're all here to build something great together.

## Getting Started

### Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/meggy-ai/bruno-core.git
cd bruno-core
```

2. **Create a virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install development dependencies**
```bash
pip install -e ".[dev,test,docs]"
```

4. **Install pre-commit hooks**
```bash
pre-commit install
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test improvements

### 2. Make Changes

Write clean, well-documented code following our style guide.

### 3. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=bruno_core --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_base.py
```

### 4. Check Code Quality

```bash
# Format code
black bruno_core/ tests/ examples/
isort bruno_core/ tests/ examples/

# Lint
flake8 bruno_core/
pylint bruno_core/

# Type checking
mypy bruno_core/
```

### 5. Commit Changes

```bash
git add .
git commit -m "feat: Add new ability interface method"
```

Commit message conventions:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test changes
- `refactor:` - Code refactoring
- `chore:` - Build process or auxiliary tool changes

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Code Style

### Python Style Guide

- Follow PEP 8
- Use Black for formatting (line length: 100)
- Use isort for import sorting
- Use type hints for all functions
- Write comprehensive docstrings (Google style)

Example:

```python
from typing import Optional

async def process_message(
    message: str,
    user_id: str,
    conversation_id: Optional[str] = None
) -> str:
    """
    Process a user message and generate a response.
    
    Args:
        message: The user's input message
        user_id: Unique identifier for the user
        conversation_id: Optional conversation identifier
        
    Returns:
        Generated response text
        
    Raises:
        ValueError: If message is empty
        
    Example:
        >>> response = await process_message("Hello", "user123")
        >>> print(response)
        "Hello! How can I help you?"
    """
    if not message:
        raise ValueError("Message cannot be empty")
    
    # Implementation here
    return response
```

### Documentation Style

- Use Markdown for documentation
- Include code examples
- Add type hints in code blocks
- Keep line length reasonable (80-100 chars)
- Use clear section headers

## Testing Guidelines

### Test Structure

```
tests/
├── unit/              # Unit tests
│   ├── test_base.py
│   └── test_models.py
├── integration/       # Integration tests
│   └── test_workflow.py
└── conftest.py        # Pytest fixtures
```

### Writing Tests

```python
import pytest
from bruno_core.base import BaseAssistant

@pytest.mark.asyncio
async def test_assistant_initialization(mock_llm, mock_memory):
    """Test that assistant initializes correctly."""
    assistant = BaseAssistant(llm=mock_llm, memory=mock_memory)
    await assistant.initialize()
    
    assert assistant.llm is not None
    assert assistant.memory is not None
    
    await assistant.shutdown()
```

### Test Coverage

- Aim for 80%+ code coverage
- Test happy paths and error cases
- Test async code properly
- Mock external dependencies

## Pull Request Process

### PR Checklist

- [ ] Code follows style guide
- [ ] Tests added/updated
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Type hints added
- [ ] Docstrings added/updated

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?

## Checklist
- [ ] Tests pass
- [ ] Code formatted
- [ ] Documentation updated
```

### Review Process

1. Automated checks must pass (CI/CD)
2. At least one approving review required
3. All conversations must be resolved
4. Branch must be up to date with main

## Documentation

### Building Documentation

```bash
# Install docs dependencies
pip install -e ".[docs]"

# Build docs
mkdocs build

# Serve docs locally
mkdocs serve
```

Visit http://127.0.0.1:8000 to view docs.

### Adding Documentation

1. Create/edit markdown files in `docs/`
2. Update `mkdocs.yml` navigation
3. Build and test locally
4. Include in PR

## Release Process

### Version Bumping

We use semantic versioning (MAJOR.MINOR.PATCH):

- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

```bash
# Update version in bruno_core/__version__.py
# Update CHANGELOG.md
# Commit changes
git commit -m "chore: Bump version to 0.2.0"
```

### Creating a Release

1. Update version number
2. Update CHANGELOG.md
3. Create git tag
```bash
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```
4. Create GitHub release (triggers PyPI publish)

## Common Tasks

### Adding a New Interface

1. Create interface in `bruno_core/interfaces/`
2. Add to `bruno_core/interfaces/__init__.py`
3. Create base implementation in `bruno_core/base/`
4. Add tests in `tests/unit/`
5. Add documentation in `docs/guides/`
6. Add example in `examples/`

### Adding a New Model

1. Create model in `bruno_core/models/`
2. Use Pydantic BaseModel
3. Add validation
4. Add to exports
5. Add tests
6. Update documentation

### Fixing a Bug

1. Create issue if not exists
2. Write failing test
3. Fix bug
4. Verify test passes
5. Update CHANGELOG.md
6. Create PR referencing issue

## Getting Help

- **Issues**: GitHub Issues for bugs/features
- **Discussions**: GitHub Discussions for questions
- **Documentation**: Read the docs first

## Recognition

Contributors will be recognized in:
- CHANGELOG.md
- GitHub contributors page
- Release notes

Thank you for contributing to Bruno Core! 🚀
