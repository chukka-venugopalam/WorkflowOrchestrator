"""Transport Factory — creates transports dynamically based on configuration.

Supports:
- REST API
- CLI
- Browser
- Desktop
- SSH
- MCP
- Local Process

All transports are selected through configuration, not hardcoded.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any, Optional

from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class TransportFactory:
    """Creates transport instances dynamically based on transport type.

    Maps transport type strings to their implementation classes and
    instantiates them with the provided configuration.

    Usage:
        >>> factory = TransportFactory()
        >>> transport = factory.create("rest_api", {"timeout": 30})
        >>> response = await transport.send(request)
    """

    # Registered transport implementations
    _TRANSPORT_TYPES: dict[str, tuple[str, str]] = {
        "rest_api": ("workflow_orchestrator.transports.rest_api_transport", "RestApiTransport"),
        "cli": ("workflow_orchestrator.transports.cli_command_transport", "CliCommandTransport"),
        "browser": ("workflow_orchestrator.transports.browser_automation_transport", "BrowserAutomationTransport"),
        "desktop": ("workflow_orchestrator.transports.desktop_automation_transport", "DesktopAutomationTransport"),
        "mcp": ("workflow_orchestrator.transports.mcp_client_transport", "McpClientTransport"),
        "ssh": ("workflow_orchestrator.transports.ssh_command_transport", "SshCommandTransport"),
    }

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Transport Factory.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus
        self._cache: dict[str, Any] = {}

    def create(self, transport_type: str, config: dict[str, Any] | None = None) -> Any | None:
        """Create a transport instance by type.

        Args:
            transport_type: Transport type string (rest_api, cli, browser, etc.).
            config: Optional configuration for the transport.

        Returns:
            Transport instance, or None if type is unknown.
        """
        transport_type = transport_type.lower()
        if transport_type not in self._TRANSPORT_TYPES:
            logger.warning("Unknown transport type: %s", transport_type)
            return None

        # Return cached instance if available
        cache_key = transport_type
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            module_path, class_name = self._TRANSPORT_TYPES[transport_type]
            module = importlib.import_module(module_path)
            transport_cls = getattr(module, class_name)

            # Create instance with config
            if config:
                instance = transport_cls(**config)
            else:
                instance = transport_cls()

            self._cache[cache_key] = instance
            self._publish_event("integration.transport_ready", {
                "transport_type": transport_type,
                "class": class_name,
            })
            return instance

        except Exception as exc:
            logger.error("Failed to create transport '%s': %s", transport_type, exc)
            return None

    def create_all(self, configs: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Create multiple transport instances.

        Args:
            configs: Dict mapping transport type to config.

        Returns:
            Dict mapping transport type to instance.
        """
        result: dict[str, Any] = {}
        for transport_type, config in configs.items():
            instance = self.create(transport_type, config)
            if instance:
                result[transport_type] = instance
        return result

    def register_type(self, name: str, module_path: str, class_name: str) -> None:
        """Register a new transport type.

        Args:
            name: Transport type name.
            module_path: Python module path.
            class_name: Class name in the module.
        """
        self._TRANSPORT_TYPES[name] = (module_path, class_name)

    def list_types(self) -> list[str]:
        """List all registered transport types.

        Returns:
            Sorted list of transport type names.
        """
        return sorted(self._TRANSPORT_TYPES.keys())

    def clear_cache(self) -> None:
        """Clear cached transport instances."""
        self._cache.clear()

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(type=event_type, data=data, source="transport_factory"))
        except Exception:
            pass
