# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure
- Core interfaces (AssistantInterface, LLMInterface, MemoryInterface, AbilityInterface)
- Base implementations (BaseAssistant, ActionExecutor, BaseAbility)
- Data models using Pydantic v2
- Plugin registry system
- Context management system
- Event bus system
- Utility modules (logging, config, validation, async helpers)
- Comprehensive test suite
- Documentation and examples

## [0.1.0] - 2025-12-07

### Added
- Initial package setup
- Project configuration (setup.py, pyproject.toml)
- Version management
- Basic package structure
- MIT License
- README documentation

[Unreleased]: https://github.com/meggy-ai/bruno-core/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/meggy-ai/bruno-core/releases/tag/v0.1.0
