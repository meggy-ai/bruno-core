"""
Interface definitions for bruno-core.

This package contains abstract base classes (ABCs) that define contracts
for all core components in the Bruno ecosystem.

These interfaces ensure:
- Consistent API across implementations
- Easy component swapping (e.g., different LLM providers)
- Clear contracts for plugin developers
- Type safety and IDE support

Modules:
    assistant: AssistantInterface - Main orchestrator interface
    llm: LLMInterface - Language model interface
    memory: MemoryInterface - Memory storage/retrieval interface
    ability: AbilityInterface - Executable action interface
    embedding: EmbeddingInterface - Vector embedding interface
    stream: StreamInterface - Streaming response interface
"""

from bruno_core.interfaces.ability import AbilityInterface
from bruno_core.interfaces.assistant import AssistantInterface
from bruno_core.interfaces.embedding import EmbeddingInterface
from bruno_core.interfaces.llm import LLMInterface
from bruno_core.interfaces.memory import MemoryInterface
from bruno_core.interfaces.stream import StreamInterface

__all__ = [
    "AssistantInterface",
    "LLMInterface",
    "MemoryInterface",
    "AbilityInterface",
    "EmbeddingInterface",
    "StreamInterface",
]
