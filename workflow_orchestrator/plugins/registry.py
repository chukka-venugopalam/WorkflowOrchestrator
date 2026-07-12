"""Plugin registry for discovering and managing workflow plugins.

Plugins can be registered manually or discovered automatically
by scanning the ``plugins`` package for subclasses of ``Plugin``.
"""

from __future__ import annotations

from typing import Any

from workflow_orchestrator.plugins.base import Plugin


class PluginRegistry:
    """Registry that manages available workflow plugins.

    Maintains a mapping of plugin names to Plugin instances.
    Provides auto-discovery and lookup by name.

    Usage:
        >>> registry = PluginRegistry()
        >>> registry.discover()
        >>> plugin = registry.get("terminal")
        >>> result = plugin.execute({"command": "git status"}, {})
    """

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin, overwrite: bool = False) -> None:
        """Register a plugin instance.

        Args:
            plugin: Plugin instance to register.
            overwrite: If True, replace an existing plugin with the same name.
                If False (default), skip registration if already registered.
        """
        name = plugin.metadata.name
        if name in self._plugins:
            if not overwrite:
                return  # Already registered; skip silently
            import logging
            logging.getLogger(__name__).warning(
                "Overwriting existing plugin '%s'", name
            )
        self._plugins[name] = plugin

    def unregister(self, name: str) -> None:
        """Remove a plugin from the registry.

        Args:
            name: Plugin name to remove.
        """
        self._plugins.pop(name, None)

    def get(self, name: str) -> Plugin | None:
        """Get a plugin by name.

        Args:
            name: Plugin identifier.

        Returns:
            Plugin or None if not found.
        """
        return self._plugins.get(name)

    def get_required(self, name: str) -> Plugin:
        """Get a plugin by name, raising an error if not found.

        Args:
            name: Plugin identifier.

        Returns:
            Plugin instance.

        Raises:
            KeyError: If no plugin with the given name is registered.
        """
        plugin = self.get(name)
        if plugin is None:
            raise KeyError(
                f"Plugin '{name}' is not registered. "
                f"Available: {list(self._plugins.keys())}"
            )
        return plugin

    def list_plugins(self) -> list[dict[str, Any]]:
        """List all registered plugins with their metadata.

        Returns:
            list[dict]: List of plugin metadata dictionaries.
        """
        return [
            {
                "name": p.metadata.name,
                "description": p.metadata.description,
                "version": p.metadata.version,
                "author": p.metadata.author,
            }
            for p in self._plugins.values()
        ]

    @property
    def names(self) -> list[str]:
        """List of registered plugin names."""
        return list(self._plugins.keys())

    @property
    def count(self) -> int:
        """Number of registered plugins."""
        return len(self._plugins)

    def discover(self, package: str = "workflow_orchestrator.plugins") -> int:
        """Auto-discover plugins by importing the plugins package.

        This relies on plugins registering themselves on import
        via a global registry, or by scanning for Plugin subclasses.

        Args:
            package: The Python package to scan for plugins.

        Returns:
            int: Number of plugins discovered.
        """
        import importlib
        import pkgutil

        try:
            pkg = importlib.import_module(package)
        except ImportError:
            return 0

        discovered = 0
        for _importer, mod_name, _is_pkg in pkgutil.iter_modules(
            pkg.__path__, prefix=f"{package}."
        ):
            if mod_name.endswith("__init__") or mod_name.endswith("base") or mod_name.endswith("registry"):
                continue
            try:
                importlib.import_module(mod_name)
                discovered += 1
            except ImportError:
                continue

        return discovered


# Singleton shared across the application
default_registry = PluginRegistry()
