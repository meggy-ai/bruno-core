"""
Memory Backend Registry.

Manages memory backend plugin discovery and registration.
"""

from typing import Type

from bruno_core.interfaces.memory import MemoryInterface
from bruno_core.registry.base import PluginRegistry
from bruno_core.utils.logging import get_logger

logger = get_logger(__name__)


class MemoryBackendRegistry(PluginRegistry):
    """
    Registry for memory backend plugins.

    Discovers and manages memory backends through the 'bruno.memory_backends' entry point group.

    Example Entry Point (setup.py):
        >>> entry_points={
        ...     'bruno.memory_backends': [
        ...         'sqlite = my_package.memory:SQLiteMemory',
        ...         'postgres = my_package.memory:PostgresMemory',
        ...         'chroma = my_package.memory:ChromaMemory',
        ...     ]
        ... }

    Usage:
        >>> registry = MemoryBackendRegistry()
        >>> registry.discover_plugins()
        >>> memory = registry.get_instance('sqlite', db_path='./memory.db')
    """

    def get_entry_point_group(self) -> str:
        """Get the entry point group for memory backends."""
        return "bruno.memory_backends"

    def validate_plugin(self, plugin_class: Type) -> bool:
        """
        Validate a memory backend plugin class.

        Args:
            plugin_class: Class to validate

        Returns:
            True if implements MemoryInterface
        """
        try:
            # Check if it's a class
            if not isinstance(plugin_class, type):
                return False

            # Check if it implements MemoryInterface (duck typing)
            required_methods = [
                "store_message",
                "retrieve_context",
                "search_memories",
                "clear_conversation",
            ]
            for method in required_methods:
                if not hasattr(plugin_class, method):
                    logger.warning(
                        "memory_backend_missing_method",
                        class_name=plugin_class.__name__,
                        method=method,
                    )
                    return False

            return True

        except Exception as e:
            logger.error("memory_backend_validation_failed", error=str(e))
            return False
