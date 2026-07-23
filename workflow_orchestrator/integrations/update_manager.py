"""Update management for providers, agents, plugins, and CLI.

Checks for updates to providers, agents, plugins, workflow templates,
and the CLI itself. Reports update availability and compatibility.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from workflow_orchestrator.core.event_bus import EventBus

logger = logging.getLogger(__name__)


class UpdateSeverity(Enum):
    """Severity level of an update."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OPTIONAL = "optional"


class UpdateType(Enum):
    """Type of update available."""
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    SECURITY = "security"
    HOTFIX = "hotfix"
    ALPHA = "alpha"
    BETA = "beta"


@dataclass
class UpdateInfo:
    """Information about an available update.

    Attributes:
        component_id: Component identifier.
        component_type: Type of component.
        current_version: Currently installed version.
        target_version: Version the update would bring.
        update_type: Type of update.
        severity: Severity of the update.
        description: Human-readable update description.
        release_notes_url: Optional URL to release notes.
        breaking_changes: Whether the update contains breaking changes.
        compatible: Whether the update is compatible with the current system.
        published_at: When the update was published.
        checked_at: When the update check was performed.
    """

    component_id: str
    component_type: str
    current_version: str
    target_version: str
    update_type: UpdateType = UpdateType.PATCH
    severity: UpdateSeverity = UpdateSeverity.LOW
    description: str = ""
    release_notes_url: Optional[str] = None
    breaking_changes: bool = False
    compatible: bool = True
    published_at: Optional[datetime] = None
    checked_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "component_id": self.component_id,
            "component_type": self.component_type,
            "current_version": self.current_version,
            "target_version": self.target_version,
            "update_type": self.update_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "release_notes_url": self.release_notes_url,
            "breaking_changes": self.breaking_changes,
            "compatible": self.compatible,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
        }


@dataclass
class UpdateReport:
    """Report of all checked updates.

    Attributes:
        updates: List of available updates.
        critical_count: Number of critical updates.
        total_checked: Number of components checked.
        checked_at: When the report was generated.
    """

    updates: List[UpdateInfo] = field(default_factory=list)
    critical_count: int = 0
    total_checked: int = 0
    checked_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "updates": [u.to_dict() for u in self.updates],
            "critical_count": self.critical_count,
            "total_checked": self.total_checked,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
        }


# Known update sources for common tools
KNOWN_UPDATE_SOURCES: Dict[str, Dict[str, Any]] = {
    "claude": {
        "type": "provider",
        "check_url": "https://api.anthropic.com/v1/version",
        "min_version": "1.0.0",
    },
    "chatgpt": {
        "type": "provider",
        "check_url": "https://api.openai.com/v1/version",
        "min_version": "1.0.0",
    },
    "gemini": {
        "type": "provider",
        "check_url": "https://generativelanguage.googleapis.com/v1/version",
        "min_version": "1.0.0",
    },
    "cursor": {
        "type": "agent",
        "check_url": "https://www.cursor.com/api/version",
        "min_version": "0.1.0",
    },
    "codex": {
        "type": "agent",
        "check_url": "https://api.openai.com/v1/codex/version",
        "min_version": "0.1.0",
    },
}


class UpdateManager:
    """Manages updates for providers, agents, plugins, and the CLI.

    Checks for available updates, tracks update history, and
    publishes update events when new versions are detected.
    """

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        """Initialize the update manager.

        Args:
            event_bus: Optional event bus for publishing update events.
        """
        self._event_bus = event_bus
        self._known_sources: Dict[str, Dict[str, Any]] = dict(KNOWN_UPDATE_SOURCES)
        self._update_history: List[UpdateInfo] = []
        self._last_report: Optional[UpdateReport] = None

    @property
    def update_count(self) -> int:
        """Get the number of tracked updates."""
        return len(self._update_history)

    def register_source(self, component_id: str, source_info: Dict[str, Any]) -> None:
        """Register a new update source.

        Args:
            component_id: Component identifier.
            source_info: Source metadata dictionary.
        """
        self._known_sources[component_id] = source_info

    def unregister_source(self, component_id: str) -> bool:
        """Remove an update source.

        Args:
            component_id: Component identifier.

        Returns:
            True if removed, False if not found.
        """
        return self._known_sources.pop(component_id, None) is not None

    def check_for_updates(self, component_ids: Optional[List[str]] = None) -> UpdateReport:
        """Check for available updates.

        Args:
            component_ids: Specific components to check, or None for all.

        Returns:
            UpdateReport with available updates.
        """
        updates: List[UpdateInfo] = []
        critical_count = 0

        sources_to_check = (
            {k: v for k, v in self._known_sources.items() if k in component_ids}
            if component_ids
            else self._known_sources
        )

        for component_id, source in sources_to_check.items():
            # In a real implementation, this would contact an update server.
            # For now, we simulate the update check.
            update = self._simulate_check(component_id, source)
            if update:
                updates.append(update)
                if update.severity == UpdateSeverity.CRITICAL:
                    critical_count += 1

        report = UpdateReport(
            updates=updates,
            critical_count=critical_count,
            total_checked=len(sources_to_check),
            checked_at=datetime.now(),
        )

        self._last_report = report
        self._update_history.extend(updates)

        if updates:
            self._publish_event("integration.update_available", {
                "update_count": len(updates),
                "critical_count": critical_count,
                "report": report.to_dict(),
            })

        return report

    def _simulate_check(self, component_id: str, source: Dict[str, Any]) -> Optional[UpdateInfo]:
        """Simulate an update check for a component.

        In production, this would contact the update server.
        For now, returns None to indicate no updates available.

        Args:
            component_id: Component identifier.
            source: Source metadata dictionary.

        Returns:
            UpdateInfo if update available, None otherwise.
        """
        # Placeholder for actual update checking logic.
        # In production, this would make HTTP requests or query package managers.
        return None

    def get_updates(self, severity: Optional[UpdateSeverity] = None) -> List[UpdateInfo]:
        """Get tracked updates, optionally filtered by severity.

        Args:
            severity: Optional severity filter.

        Returns:
            List of UpdateInfo instances.
        """
        if severity:
            return [u for u in self._update_history if u.severity == severity]
        return list(self._update_history)

    def get_critical_updates(self) -> List[UpdateInfo]:
        """Get all critical updates.

        Returns:
            List of critical UpdateInfo instances.
        """
        return self.get_updates(UpdateSeverity.CRITICAL)

    def get_last_report(self) -> Optional[UpdateReport]:
        """Get the last update check report.

        Returns:
            The last UpdateReport, or None if none performed.
        """
        return self._last_report

    def clear_history(self) -> None:
        """Clear update history."""
        self._update_history.clear()
        self._last_report = None

    def _publish_event(self, event: str, data: Dict[str, Any]) -> None:
        """Publish an event through the event bus.

        Args:
            event: Event name.
            data: Event payload.
        """
        if self._event_bus:
            self._event_bus.publish(event, data)
