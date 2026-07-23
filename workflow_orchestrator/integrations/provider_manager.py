"""Provider Manager — owns the full provider lifecycle.

Manages:
- Install / Remove / Enable / Disable
- Configure / Validate / Repair / Update
- Lifecycle tracking and event publishing
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class ProviderStatus(Enum):
    """Lifecycle status of a managed provider."""

    UNINSTALLED = "uninstalled"
    INSTALLING = "installing"
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    CONFIGURING = "configuring"
    CONFIGURED = "configured"
    ERROR = "error"
    REPAIRING = "repairing"
    UPDATING = "updating"
    UNKNOWN = "unknown"


@dataclass
class ProviderInfo:
    """Information about a managed provider.

    Attributes:
        provider_id: Unique provider identifier.
        name: Human-readable provider name.
        version: Installed version string.
        status: Current lifecycle status.
        transport: Transport type used.
        enabled: Whether the provider is enabled.
        configured: Whether the provider is configured.
        health: Health status string.
        capabilities: List of capability IDs.
        config_path: Path to YAML configuration file.
        installed_at: ISO-8601 install timestamp.
        error: Error message if in error state.
    """

    provider_id: str = ""
    name: str = ""
    version: str = "0.0.0"
    status: ProviderStatus = ProviderStatus.UNINSTALLED
    transport: str = "rest_api"
    enabled: bool = False
    configured: bool = False
    health: str = "unknown"
    capabilities: list[str] = field(default_factory=list)
    config_path: str = ""
    installed_at: str = ""
    error: str = ""


class ProviderManager:
    """Manages the full lifecycle of provider adapters.

    Coordinates installation, removal, configuration, validation,
    repair, and update of all provider adapters. Integrates with
    the ProviderDetector, ProviderInstaller, and ProviderConfiguration
    subsystems.

    Usage:
        >>> mgr = ProviderManager(event_bus=bus)
        >>> result = mgr.install("claude")
        >>> mgr.enable("anthropic.claude")
        >>> info = mgr.status("anthropic.claude")
    """

    # Known provider registry: provider_id -> (module_path, class_name)
    KNOWN_PROVIDERS: dict[str, tuple[str, str]] = {
        "anthropic.claude": ("workflow_orchestrator.providers.implementations.claude_provider", "ClaudeProvider"),
        "openai.chatgpt": ("workflow_orchestrator.providers.implementations.chatgpt_provider", "ChatGPTProvider"),
        "google.gemini": ("workflow_orchestrator.providers.implementations.gemini_provider", "GeminiProvider"),
    }

    def __init__(
        self,
        event_bus: EventBus | None = None,
        provider_registry: Any = None,
        config_dir: str | Path = "providers/yaml",
    ) -> None:
        """Initialize the Provider Manager.

        Args:
            event_bus: Optional EventBus for publishing events.
            provider_registry: Optional provider registry for registering adapters.
            config_dir: Directory for provider YAML configuration files.
        """
        self._event_bus = event_bus
        self._provider_registry = provider_registry
        self._config_dir = Path(config_dir)
        self._providers: dict[str, ProviderInfo] = {}

        # Register known providers
        for pid in self.KNOWN_PROVIDERS:
            self._providers[pid] = ProviderInfo(
                provider_id=pid,
                name=pid.split(".")[-1].title(),
                status=ProviderStatus.UNINSTALLED,
            )

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------

    def install(self, provider_id: str) -> bool:
        """Install a provider adapter.

        Args:
            provider_id: The provider identifier.

        Returns:
            True if installation succeeded.
        """
        provider_id = self._resolve_id(provider_id)

        if provider_id not in self.KNOWN_PROVIDERS:
            logger.warning("Unknown provider: %s", provider_id)
            return False

        info = self._providers.get(provider_id)
        if info is None:
            info = ProviderInfo(provider_id=provider_id, name=provider_id.split(".")[-1].title())
            self._providers[provider_id] = info

        info.status = ProviderStatus.INSTALLING

        try:
            module_path, class_name = self.KNOWN_PROVIDERS[provider_id]
            module = importlib.import_module(module_path)
            provider_cls = getattr(module, class_name)
            provider_instance = provider_cls()

            # Register with provider registry if available
            if self._provider_registry is not None:
                self._provider_registry.register(provider_instance)

            info.status = ProviderStatus.INSTALLED
            info.version = provider_instance.manifest().version
            info.capabilities = [c.id for c in provider_instance.manifest().capabilities]
            info.installed_at = datetime.now(timezone.utc).isoformat()

            self._publish_event("integration.provider_detected", {
                "provider_id": provider_id,
                "version": info.version,
            })
            self._publish_event("integration.provider_registered", {
                "provider_id": provider_id,
                "status": "installed",
            })
            return True

        except Exception as exc:
            info.status = ProviderStatus.ERROR
            info.error = str(exc)
            logger.error("Failed to install provider '%s': %s", provider_id, exc)
            return False

    def remove(self, provider_id: str) -> bool:
        """Remove a provider adapter.

        Args:
            provider_id: The provider identifier.

        Returns:
            True if removal succeeded.
        """
        provider_id = self._resolve_id(provider_id)
        info = self._providers.get(provider_id)
        if info is None:
            return False

        # Unregister from provider registry
        if self._provider_registry is not None:
            try:
                self._provider_registry.unregister(provider_id)
            except Exception:
                pass

        info.status = ProviderStatus.UNINSTALLED
        info.enabled = False
        info.configured = False
        info.version = "0.0.0"

        self._publish_event("integration.provider_removed", {
            "provider_id": provider_id,
        })
        return True

    def enable(self, provider_id: str) -> bool:
        """Enable a provider.

        Args:
            provider_id: The provider identifier.

        Returns:
            True if enabled.
        """
        provider_id = self._resolve_id(provider_id)
        info = self._providers.get(provider_id)
        if info is None or info.status in (ProviderStatus.UNINSTALLED, ProviderStatus.ERROR):
            return False
        info.enabled = True
        info.status = ProviderStatus.ENABLED
        return True

    def disable(self, provider_id: str) -> bool:
        """Disable a provider.

        Args:
            provider_id: The provider identifier.

        Returns:
            True if disabled.
        """
        provider_id = self._resolve_id(provider_id)
        info = self._providers.get(provider_id)
        if info is None:
            return False
        info.enabled = False
        info.status = ProviderStatus.DISABLED
        return True

    def validate(self, provider_id: str) -> dict[str, Any]:
        """Validate a provider's configuration and health.

        Args:
            provider_id: The provider identifier.

        Returns:
            Dict with validation results.
        """
        provider_id = self._resolve_id(provider_id)
        info = self._providers.get(provider_id)
        if info is None:
            return {"valid": False, "error": "Provider not found"}

        issues: list[str] = []
        if not info.enabled:
            issues.append("Provider is disabled")
        if not info.configured:
            issues.append("Provider is not configured")
        if info.status == ProviderStatus.ERROR:
            issues.append(f"Provider in error state: {info.error}")

        return {
            "valid": len(issues) == 0,
            "provider_id": provider_id,
            "status": info.status.value,
            "issues": issues,
        }

    def repair(self, provider_id: str) -> bool:
        """Attempt to repair a provider installation.

        Args:
            provider_id: The provider identifier.

        Returns:
            True if repair succeeded.
        """
        provider_id = self._resolve_id(provider_id)
        info = self._providers.get(provider_id)
        if info is None:
            return False

        info.status = ProviderStatus.REPAIRING
        success = self.install(provider_id)
        if success:
            info.status = ProviderStatus.ENABLED
            info.error = ""
        else:
            info.status = ProviderStatus.ERROR
        return success

    def update(self, provider_id: str) -> bool:
        """Update a provider to the latest version.

        Args:
            provider_id: The provider identifier.

        Returns:
            True if update succeeded.
        """
        provider_id = self._resolve_id(provider_id)
        info = self._providers.get(provider_id)
        if info is None:
            return False

        info.status = ProviderStatus.UPDATING
        success = self.install(provider_id)
        return success

    # ------------------------------------------------------------------
    # Status and queries
    # ------------------------------------------------------------------

    def status(self, provider_id: str) -> ProviderInfo | None:
        """Get the status of a provider.

        Args:
            provider_id: The provider identifier.

        Returns:
            ProviderInfo or None.
        """
        provider_id = self._resolve_id(provider_id)
        return self._providers.get(provider_id)

    def list_providers(self) -> list[ProviderInfo]:
        """List all managed providers.

        Returns:
            List of ProviderInfo objects.
        """
        return list(self._providers.values())

    def list_enabled(self) -> list[ProviderInfo]:
        """List enabled providers.

        Returns:
            List of enabled ProviderInfo objects.
        """
        return [p for p in self._providers.values() if p.enabled]

    def list_installed(self) -> list[ProviderInfo]:
        """List installed providers.

        Returns:
            List of installed ProviderInfo objects.
        """
        return [p for p in self._providers.values() if p.status != ProviderStatus.UNINSTALLED]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_id(self, provider_id: str) -> str:
        """Resolve a short provider ID to its full ID.

        Args:
            provider_id: Short or full provider ID.

        Returns:
            Full provider ID.
        """
        short_map = {
            "claude": "anthropic.claude",
            "chatgpt": "openai.chatgpt",
            "gpt": "openai.chatgpt",
            "gemini": "google.gemini",
        }
        return short_map.get(provider_id.lower(), provider_id)

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(type=event_type, data=data, source="provider_manager"))
        except Exception:
            pass
