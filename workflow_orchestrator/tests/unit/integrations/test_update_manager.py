"""Tests for UpdateManager integration module."""

from __future__ import annotations

from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from workflow_orchestrator.integrations.update_manager import (
    UpdateInfo,
    UpdateManager,
    UpdateReport,
    UpdateSeverity,
    UpdateType,
)


class TestUpdateInfo:
    """Tests for UpdateInfo data class."""

    def test_create(self) -> None:
        info = UpdateInfo(
            component_id="claude",
            component_type="provider",
            current_version="1.0.0",
            target_version="1.1.0",
        )
        assert info.component_id == "claude"
        assert info.current_version == "1.0.0"
        assert info.target_version == "1.1.0"
        assert info.severity == UpdateSeverity.LOW

    def test_to_dict(self) -> None:
        info = UpdateInfo(
            component_id="test", component_type="cli",
            current_version="1.0", target_version="1.1",
        )
        d = info.to_dict()
        assert d["component_id"] == "test"
        assert d["update_type"] == "patch"

    def test_critical_severity(self) -> None:
        info = UpdateInfo(
            component_id="security-fix", component_type="provider",
            current_version="1.0", target_version="1.0.1",
            severity=UpdateSeverity.CRITICAL,
        )
        assert info.severity == UpdateSeverity.CRITICAL


class TestUpdateReport:
    """Tests for UpdateReport data class."""

    def test_empty(self) -> None:
        report = UpdateReport()
        assert report.updates == []
        assert report.critical_count == 0
        assert report.total_checked == 0

    def test_with_updates(self) -> None:
        updates = [
            UpdateInfo("c1", "provider", "1.0", "1.1"),
            UpdateInfo("c2", "cli", "2.0", "2.1", severity=UpdateSeverity.CRITICAL),
        ]
        report = UpdateReport(updates=updates, total_checked=2, critical_count=1)
        assert report.total_checked == 2
        assert report.critical_count == 1

    def test_to_dict(self) -> None:
        report = UpdateReport(updates=[], total_checked=5)
        d = report.to_dict()
        assert d["total_checked"] == 5
        assert d["critical_count"] == 0


class TestUpdateManager:
    """Tests for UpdateManager class."""

    def test_initial_state(self) -> None:
        event_bus = MagicMock()
        manager = UpdateManager(event_bus=event_bus)
        assert manager.update_count == 0

    def test_check_updates(self) -> None:
        event_bus = MagicMock()
        manager = UpdateManager(event_bus=event_bus)
        report = manager.check_for_updates()
        assert isinstance(report, UpdateReport)
        assert report.total_checked >= 0

    def test_register_source(self) -> None:
        event_bus = MagicMock()
        manager = UpdateManager(event_bus=event_bus)
        source_info = {"type": "provider", "check_url": "https://example.com/version"}
        manager.register_source("custom-tool", source_info)
        report = manager.check_for_updates(component_ids=["custom-tool"])
        assert report.total_checked == 1

    def test_unregister_source(self) -> None:
        event_bus = MagicMock()
        manager = UpdateManager(event_bus=event_bus)
        manager.register_source("test", {"type": "test"})
        result = manager.unregister_source("test")
        assert result is True

    def test_unregister_nonexistent(self) -> None:
        event_bus = MagicMock()
        manager = UpdateManager(event_bus=event_bus)
        result = manager.unregister_source("nonexistent")
        assert result is False

    def test_get_updates(self) -> None:
        event_bus = MagicMock()
        manager = UpdateManager(event_bus=event_bus)
        report = manager.check_for_updates()
        updates = manager.get_updates()
        assert isinstance(updates, list)

    def test_get_critical_updates(self) -> None:
        event_bus = MagicMock()
        manager = UpdateManager(event_bus=event_bus)
        critical = manager.get_critical_updates()
        assert isinstance(critical, list)

    def test_clear_history(self) -> None:
        event_bus = MagicMock()
        manager = UpdateManager(event_bus=event_bus)
        manager.clear_history()
        assert manager.update_count == 0

    def test_get_last_report(self) -> None:
        event_bus = MagicMock()
        manager = UpdateManager(event_bus=event_bus)
        report = manager.check_for_updates()
        last = manager.get_last_report()
        assert last is not None
        assert last.total_checked == report.total_checked

    def test_no_event_bus(self) -> None:
        manager = UpdateManager(event_bus=None)
        report = manager.check_for_updates()
        assert report.total_checked >= 0
