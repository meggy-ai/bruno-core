"""
Plugin Registry System.

Provides automatic discovery and registration of abilities, LLM providers,
and memory backends through Python entry points.
"""

from bruno_core.registry.ability_registry import AbilityRegistry
from bruno_core.registry.base import PluginInfo, PluginRegistry
from bruno_core.registry.llm_registry import LLMProviderRegistry
from bruno_core.registry.memory_registry import MemoryBackendRegistry

__all__ = [
    "AbilityRegistry",
    "LLMProviderRegistry",
    "MemoryBackendRegistry",
    "PluginRegistry",
    "PluginInfo",
]
