"""
Base registry implementation for plugins.

Provides common functionality for all plugin registries.
"""

import importlib.metadata
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

from bruno_core.utils.exceptions import RegistryError, ValidationError
from bruno_core.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PluginInfo:
    """
    Information about a registered plugin.

    Attributes:
        name: Plugin name
        entry_point: Entry point name (if loaded via entry points)
        plugin_class: Plugin class
        version: Plugin version
        dependencies: List of required dependencies
        metadata: Additional metadata
    """

    name: str
    plugin_class: Type
    version: str = "0.0.0"
    entry_point: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate plugin info after initialization."""
        if not self.name:
            raise ValidationError("Plugin name cannot be empty")


class PluginRegistry(ABC):
    """
    Base class for plugin registries.

    Provides common functionality for discovering, registering, and managing plugins.
    Subclasses should implement get_entry_point_group() to specify which entry point
    group to scan.

    Example:
        >>> class MyRegistry(PluginRegistry):
        ...     def get_entry_point_group(self):
        ...         return "my_app.plugins"
        ...
        ...     def validate_plugin(self, plugin_class):
        ...         return issubclass(plugin_class, MyPluginBase)
    """

    def __init__(self) -> None:
        """Initialize plugin registry."""
        self._plugins: Dict[str, PluginInfo] = {}
        self._instances: Dict[str, Any] = {}
        logger.info("registry_initialized", registry=self.__class__.__name__)

    @abstractmethod
    def get_entry_point_group(self) -> str:
        """
        Get the entry point group name for this registry.

        Returns:
            Entry point group name (e.g., "bruno.abilities")
        """
        pass

    @abstractmethod
    def validate_plugin(self, plugin_class: Type) -> bool:
        """
        Validate a plugin class.

        Args:
            plugin_class: Class to validate

        Returns:
            True if valid
        """
        pass

    def discover_plugins(self) -> None:
        """
        Discover and register plugins from entry points.

        Scans the entry point group and registers all found plugins.
        """
        group = self.get_entry_point_group()
        logger.info("discovering_plugins", group=group)

        try:
            entry_points = importlib.metadata.entry_points()

            # Handle both dict and list-like entry point objects
            if hasattr(entry_points, "select"):
                # Python 3.10+ style
                group_eps = entry_points.select(group=group)
            elif isinstance(entry_points, dict):
                # Python 3.9 style
                group_eps = entry_points.get(group, [])
            else:
                # Older style - filter by group
                group_eps = [ep for ep in entry_points if ep.group == group]

            for entry_point in group_eps:
                try:
                    plugin_class = entry_point.load()
                    self.register(
                        name=entry_point.name,
                        plugin_class=plugin_class,
                        entry_point=entry_point.name,
                    )
                    logger.info(
                        "plugin_discovered",
                        name=entry_point.name,
                        group=group,
                    )
                except Exception as e:
                    logger.error(
                        "plugin_discovery_failed",
                        entry_point=entry_point.name,
                        error=str(e),
                    )

        except Exception as e:
            logger.error("discovery_failed", group=group, error=str(e))

    def register(
        self,
        name: str,
        plugin_class: Type,
        version: str = "0.0.0",
        entry_point: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register a plugin.

        Args:
            name: Plugin name
            plugin_class: Plugin class
            version: Plugin version
            entry_point: Entry point name (if discovered)
            dependencies: List of dependencies
            metadata: Additional metadata

        Raises:
            RegistryError: If plugin is invalid or already registered
        """
        # Validate plugin
        if not self.validate_plugin(plugin_class):
            raise RegistryError(
                f"Invalid plugin class: {plugin_class}",
                details={"name": name, "class": str(plugin_class)},
            )

        # Check if already registered
        if name in self._plugins:
            logger.warning("plugin_already_registered", name=name)
            return

        # Create plugin info
        info = PluginInfo(
            name=name,
            plugin_class=plugin_class,
            version=version,
            entry_point=entry_point,
            dependencies=dependencies or [],
            metadata=metadata or {},
        )

        self._plugins[name] = info
        logger.info("plugin_registered", name=name, version=version)

    def unregister(self, name: str) -> None:
        """
        Unregister a plugin.

        Args:
            name: Plugin name

        Raises:
            RegistryError: If plugin not found
        """
        if name not in self._plugins:
            raise RegistryError(
                f"Plugin not found: {name}",
                details={"name": name},
            )

        # Remove instance if exists
        if name in self._instances:
            del self._instances[name]

        del self._plugins[name]
        logger.info("plugin_unregistered", name=name)

    def get(self, name: str) -> Optional[PluginInfo]:
        """
        Get plugin info by name.

        Args:
            name: Plugin name

        Returns:
            PluginInfo or None if not found
        """
        return self._plugins.get(name)

    def get_instance(self, name: str, **kwargs: Any) -> Any:
        """
        Get or create a plugin instance.

        Args:
            name: Plugin name
            **kwargs: Arguments to pass to plugin constructor

        Returns:
            Plugin instance

        Raises:
            RegistryError: If plugin not found
        """
        if name not in self._plugins:
            raise RegistryError(
                f"Plugin not found: {name}",
                details={"name": name},
            )

        # Return cached instance if exists and no kwargs provided
        if name in self._instances and not kwargs:
            return self._instances[name]

        # Create new instance
        info = self._plugins[name]
        try:
            instance = info.plugin_class(**kwargs)

            # Cache if no kwargs (shared instance)
            if not kwargs:
                self._instances[name] = instance

            logger.info("plugin_instantiated", name=name)
            return instance

        except Exception as e:
            raise RegistryError(
                f"Failed to instantiate plugin: {name}",
                details={"name": name, "error": str(e)},
                cause=e,
            )

    def list_plugins(self) -> List[str]:
        """
        List all registered plugin names.

        Returns:
            List of plugin names
        """
        return list(self._plugins.keys())

    def get_all_plugins(self) -> Dict[str, PluginInfo]:
        """
        Get all registered plugins.

        Returns:
            Dict of plugin name to PluginInfo
        """
        return self._plugins.copy()

    def clear(self) -> None:
        """Clear all registered plugins and instances."""
        self._plugins.clear()
        self._instances.clear()
        logger.info("registry_cleared", registry=self.__class__.__name__)

    def has_plugin(self, name: str) -> bool:
        """
        Check if a plugin is registered.

        Args:
            name: Plugin name

        Returns:
            True if registered
        """
        return name in self._plugins
