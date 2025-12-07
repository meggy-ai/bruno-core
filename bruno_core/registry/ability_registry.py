"""
Ability Registry.

Manages ability plugin discovery and registration.
"""

from typing import Type

from bruno_core.interfaces.ability import AbilityInterface
from bruno_core.registry.base import PluginRegistry
from bruno_core.utils.logging import get_logger

logger = get_logger(__name__)


class AbilityRegistry(PluginRegistry):
    """
    Registry for ability plugins.

    Discovers and manages abilities through the 'bruno.abilities' entry point group.

    Example Entry Point (setup.py):
        >>> entry_points={
        ...     'bruno.abilities': [
        ...         'timer = my_package.abilities:TimerAbility',
        ...         'music = my_package.abilities:MusicAbility',
        ...     ]
        ... }

    Usage:
        >>> registry = AbilityRegistry()
        >>> registry.discover_plugins()
        >>> timer = registry.get_instance('timer')
    """

    def get_entry_point_group(self) -> str:
        """Get the entry point group for abilities."""
        return "bruno.abilities"

    def validate_plugin(self, plugin_class: Type) -> bool:
        """
        Validate an ability plugin class.

        Args:
            plugin_class: Class to validate

        Returns:
            True if implements AbilityInterface
        """
        try:
            # Check if it's a class
            if not isinstance(plugin_class, type):
                return False

            # Check if it implements AbilityInterface (duck typing)
            required_methods = ["execute", "get_metadata", "can_handle"]
            for method in required_methods:
                if not hasattr(plugin_class, method):
                    logger.warning(
                        "ability_missing_method",
                        class_name=plugin_class.__name__,
                        method=method,
                    )
                    return False

            return True

        except Exception as e:
            logger.error("ability_validation_failed", error=str(e))
            return False
