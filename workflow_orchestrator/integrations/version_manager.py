"""Version and compatibility tracking for providers, agents, and CLI tools.

This module manages version information for all integrated components,
tracks compatibility constraints, minimum version requirements, and
update availability.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from workflow_orchestrator.core.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class ComponentVersion:
    """Version information for a single component.

    Attributes:
        component_id: Unique identifier for the component.
        component_type: Type (provider, agent, cli, plugin, transport).
        installed_version: Currently installed version string.
        latest_version: Latest available version (None if unknown).
        min_version: Minimum required version for compatibility.
        compatible: Whether the installed version is compatible.
        update_available: Whether a newer version is available.
        checked_at: When version info was last checked.
        metadata: Additional version metadata.
    """

    component_id: str
    component_type: str
    installed_version: str = ""
    latest_version: Optional[str] = None
    min_version: str = "0.0.0"
    compatible: bool = True
    update_available: bool = False
    checked_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "component_id": self.component_id,
            "component_type": self.component_type,
            "installed_version": self.installed_version,
            "latest_version": self.latest_version,
            "min_version": self.min_version,
            "compatible": self.compatible,
            "update_available": self.update_available,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ComponentVersion:
        """Deserialize from dictionary."""
        checked_at = data.get("checked_at")
        if isinstance(checked_at, str):
            checked_at = datetime.fromisoformat(checked_at)
        return cls(
            component_id=data["component_id"],
            component_type=data.get("component_type", "unknown"),
            installed_version=data.get("installed_version", ""),
            latest_version=data.get("latest_version"),
            min_version=data.get("min_version", "0.0.0"),
            compatible=data.get("compatible", True),
            update_available=data.get("update_available", False),
            checked_at=checked_at,
            metadata=data.get("metadata", {}),
        )


# Known minimum version requirements for common tools
DEFAULT_MIN_VERSIONS: Dict[str, str] = {
    "python": "3.9.0",
    "node": "16.0.0",
    "git": "2.20.0",
    "docker": "20.10.0",
    "claude": "1.0.0",
    "chatgpt": "1.0.0",
    "gemini": "1.0.0",
    "cursor": "0.1.0",
    "codex": "0.1.0",
    "copilot": "1.0.0",
}


def _parse_version(version_str: str) -> Tuple[int, ...]:
    """Parse a version string into a comparable tuple of integers.

    Args:
        version_str: Version string (e.g., '1.2.3').

    Returns:
        Tuple of integers for comparison.
    """
    try:
        parts = version_str.replace("-", ".").split(".")
        result = []
        for part in parts:
            try:
                result.append(int(part))
            except ValueError:
                result.append(0)
        return tuple(result)
    except (ValueError, AttributeError):
        return (0, 0, 0)


def _compare_versions(v1: str, v2: str) -> int:
    """Compare two version strings.

    Args:
        v1: First version string.
        v2: Second version string.

    Returns:
        -1 if v1 < v2, 0 if equal, 1 if v1 > v2.
    """
    t1 = _parse_version(v1)
    t2 = _parse_version(v2)
    if t1 < t2:
        return -1
    if t1 > t2:
        return 1
    return 0


class VersionManager:
    """Tracks versions, compatibility, and updates for all components.

    Maintains a registry of component versions, checks compatibility
    against minimum version requirements, and tracks update availability.
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        versions_file: Optional[Path] = None,
    ) -> None:
        """Initialize the version manager.

        Args:
            event_bus: Optional event bus for publishing version events.
            versions_file: Optional path for persisting version data.
        """
        self._event_bus = event_bus
        self._versions_file = versions_file or Path(".state/versions.json")
        self._components: Dict[str, ComponentVersion] = {}
        self._min_versions: Dict[str, str] = dict(DEFAULT_MIN_VERSIONS)
        self._loaded = False

    @property
    def component_count(self) -> int:
        """Get the number of tracked components."""
        return len(self._components)

    def set_min_version(self, component_id: str, version: str) -> None:
        """Set the minimum required version for a component.

        Args:
            component_id: Component identifier.
            version: Minimum version string.
        """
        self._min_versions[component_id] = version

    def get_min_version(self, component_id: str) -> str:
        """Get the minimum required version for a component.

        Args:
            component_id: Component identifier.

        Returns:
            Minimum version string or '0.0.0' if not set.
        """
        return self._min_versions.get(component_id, "0.0.0")

    def register_version(self, component_id: str, component_type: str, installed_version: str, metadata: Optional[Dict[str, Any]] = None) -> ComponentVersion:
        """Register or update a component's version.

        Args:
            component_id: Unique component identifier.
            component_type: Type (provider, agent, cli, etc.).
            installed_version: Installed version string.
            metadata: Optional additional metadata.

        Returns:
            The registered ComponentVersion.
        """
        min_ver = self.get_min_version(component_id)
        compatible = _compare_versions(installed_version, min_ver) >= 0

        existing = self._components.get(component_id)
        if existing:
            existing.installed_version = installed_version
            existing.min_version = min_ver
            existing.compatible = compatible
            existing.checked_at = datetime.now()
            if metadata:
                existing.metadata.update(metadata)
            component = existing
        else:
            component = ComponentVersion(
                component_id=component_id,
                component_type=component_type,
                installed_version=installed_version,
                min_version=min_ver,
                compatible=compatible,
                checked_at=datetime.now(),
                metadata=metadata or {},
            )
            self._components[component_id] = component

        self._publish_event("integration.version_registered", {
            "component_id": component_id,
            "component_type": component_type,
            "version": installed_version,
            "compatible": compatible,
        })

        return component

    def check_compatibility(self, component_id: str) -> bool:
        """Check if a component's installed version meets minimum requirements.

        Args:
            component_id: Component identifier.

        Returns:
            True if compatible or unknown, False if below minimum.
        """
        component = self._components.get(component_id)
        if not component:
            return True
        return component.compatible

    def get_version(self, component_id: str) -> Optional[ComponentVersion]:
        """Get version info for a component.

        Args:
            component_id: Component identifier.

        Returns:
            ComponentVersion if found, None otherwise.
        """
        return self._components.get(component_id)

    def list_versions(self, component_type: Optional[str] = None) -> List[ComponentVersion]:
        """List all tracked component versions.

        Args:
            component_type: Optional filter by type.

        Returns:
            List of ComponentVersion instances.
        """
        if component_type:
            return [c for c in self._components.values() if c.component_type == component_type]
        return list(self._components.values())

    def get_incompatible_components(self) -> List[ComponentVersion]:
        """Get all components with incompatible versions.

        Returns:
            List of incompatible ComponentVersion instances.
        """
        return [c for c in self._components.values() if not c.compatible]

    def get_outdated_components(self) -> List[ComponentVersion]:
        """Get all components with updates available.

        Returns:
            List of outdated ComponentVersion instances.
        """
        return [c for c in self._components.values() if c.update_available]

    def set_latest_version(self, component_id: str, latest_version: str) -> None:
        """Set the latest available version for a component.

        Args:
            component_id: Component identifier.
            latest_version: Latest version string.
        """
        component = self._components.get(component_id)
        if component:
            component.latest_version = latest_version
            component.update_available = _compare_versions(latest_version, component.installed_version) > 0

    def save(self) -> None:
        """Persist version data to disk."""
        data = {
            "components": {k: v.to_dict() for k, v in self._components.items()},
            "min_versions": dict(self._min_versions),
        }
        self._versions_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self._versions_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError as exc:
            logger.error("Failed to save versions: %s", exc)

    def load(self) -> None:
        """Load version data from disk."""
        if not self._versions_file.exists():
            self._loaded = True
            return
        try:
            with open(self._versions_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._components = {
                k: ComponentVersion.from_dict(v)
                for k, v in data.get("components", {}).items()
            }
            self._min_versions.update(data.get("min_versions", {}))
            self._loaded = True
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load versions: %s", exc)
            self._loaded = True

    def _publish_event(self, event: str, data: Dict[str, Any]) -> None:
        """Publish an event through the event bus.

        Args:
            event: Event name.
            data: Event payload.
        """
        if self._event_bus:
            self._event_bus.publish(event, data)
