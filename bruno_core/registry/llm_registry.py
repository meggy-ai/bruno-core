"""
LLM Provider Registry.

Manages LLM provider plugin discovery and registration.
"""

from typing import Type

from bruno_core.interfaces.llm import LLMInterface
from bruno_core.registry.base import PluginRegistry
from bruno_core.utils.logging import get_logger

logger = get_logger(__name__)


class LLMProviderRegistry(PluginRegistry):
    """
    Registry for LLM provider plugins.

    Discovers and manages LLM providers through the 'bruno.llm_providers' entry point group.

    Example Entry Point (setup.py):
        >>> entry_points={
        ...     'bruno.llm_providers': [
        ...         'openai = my_package.llm:OpenAIProvider',
        ...         'claude = my_package.llm:ClaudeProvider',
        ...         'ollama = my_package.llm:OllamaProvider',
        ...     ]
        ... }

    Usage:
        >>> registry = LLMProviderRegistry()
        >>> registry.discover_plugins()
        >>> openai = registry.get_instance('openai', api_key='...')
    """

    def get_entry_point_group(self) -> str:
        """Get the entry point group for LLM providers."""
        return "bruno.llm_providers"

    def validate_plugin(self, plugin_class: Type) -> bool:
        """
        Validate an LLM provider plugin class.

        Args:
            plugin_class: Class to validate

        Returns:
            True if implements LLMInterface
        """
        try:
            # Check if it's a class
            if not isinstance(plugin_class, type):
                return False

            # Check if it implements LLMInterface (duck typing)
            required_methods = ["generate", "stream", "get_token_count", "list_models"]
            for method in required_methods:
                if not hasattr(plugin_class, method):
                    logger.warning(
                        "llm_provider_missing_method",
                        class_name=plugin_class.__name__,
                        method=method,
                    )
                    return False

            return True

        except Exception as e:
            logger.error("llm_provider_validation_failed", error=str(e))
            return False
