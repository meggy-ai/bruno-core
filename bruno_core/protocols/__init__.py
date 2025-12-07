"""
Protocol definitions for bruno-core.

Provides runtime-checkable protocols for structural subtyping.

Protocols allow duck-typing while maintaining type safety. They are
an alternative to ABC inheritance that's more flexible.

Example:
    >>> from bruno_core.protocols import LLMProtocol
    >>> 
    >>> class MyLLM:  # No inheritance needed!
    ...     async def generate(self, messages, **kwargs):
    ...         return "response"
    >>> 
    >>> llm = MyLLM()
    >>> isinstance(llm, LLMProtocol)  # Runtime check
    True
"""

from bruno_core.protocols.interfaces import (
    AssistantProtocol,
    LLMProtocol,
    MemoryProtocol,
    AbilityProtocol,
    EmbeddingProtocol,
    StreamProtocol,
)

__all__ = [
    "AssistantProtocol",
    "LLMProtocol",
    "MemoryProtocol",
    "AbilityProtocol",
    "EmbeddingProtocol",
    "StreamProtocol",
]
