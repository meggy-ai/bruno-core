"""
Bruno Core - Foundation package for the Bruno AI Assistant ecosystem.

This package provides the core interfaces, base implementations, and utilities
that other Bruno packages build upon. It enables building modular, extensible
AI assistants with swappable components.

Core Components:
    - Interfaces: Abstract contracts for LLM, Memory, Abilities, etc.
    - Base Classes: Default implementations that can be extended
    - Models: Pydantic data models for type safety
    - Registry: Plugin system for dynamic component discovery
    - Context: Conversation and session management
    - Events: Event bus for inter-component communication
    - Utils: Common utilities for logging, config, validation

Example:
    >>> from bruno_core import BaseAssistant
    >>> from bruno_core.models import BrunoRequest
    >>> 
    >>> # Create an assistant instance
    >>> assistant = BaseAssistant(llm=my_llm, memory=my_memory)
    >>> 
    >>> # Process a message
    >>> request = BrunoRequest(
    ...     user_id="user_123",
    ...     channel="cli",
    ...     text="Hello, Bruno!"
    ... )
    >>> response = await assistant.process_message(request)
    >>> print(response.text)
"""

from bruno_core.__version__ import (
    __version__,
    __version_info__,
    __title__,
    __description__,
    __author__,
    __author_email__,
    __license__,
    __url__,
)

# Version will be importable as: from bruno_core import __version__
__all__ = [
    "__version__",
    "__version_info__",
    "__title__",
    "__description__",
    "__author__",
    "__author_email__",
    "__license__",
    "__url__",
]

# Note: Specific components will be imported from their respective modules
# For example:
#   from bruno_core.interfaces import AssistantInterface, LLMInterface
#   from bruno_core.base import BaseAssistant
#   from bruno_core.models import Message, BrunoRequest, BrunoResponse
