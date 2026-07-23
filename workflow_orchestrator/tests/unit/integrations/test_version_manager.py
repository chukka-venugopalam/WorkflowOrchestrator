"""Tests for VersionManager integration module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, Optional
from unittest.mock import MagicMock, patch

import pytest

from workflow_orchestrator.integrations.version_manager import (
    ComponentVersion,
    VersionManager,
    _parse_version,
    _compare_versions,
    DEFAULT_MIN_VERSIONS,
)


class TestVersionParsing:
    """Tests for version comparison utilities."""

    def test_parse_simple(self) -> None:
        assert _parse_version("1.2.3") == (1, 2, 3)

    def test_parse_dev(self) -> None:
        assert _parse_version("1.2.3-dev") == (1, 2, 3, 0)

    def test_parse_rc(self) -> None:
        assert _parse_version("2.0.0-rc1") == (2, 0, 0, 0)

    def test_parse_empty_returns_zero_tuple(self) -> None:
        result = _parse_version("")
        assert len(result) >= 1
        assert all(v == 0 for v in result)

    def test_parse_invalid_returns_zero_tuple(self) -> None:
        result = _parse_version("abc")
        assert len(result) >= 1
        assert all(v == 0 for v in result)

    def test_compare_equal(self) -> None:
        assert _compare_versions("1.0.0", "1.0.0") == 0

    def test_compare_less(self) -> None:
        assert _compare_versions("1.0.0", "2.0.0") == -1

    def test_compare_greater(self) -> None:
        assert _compare_versions("2.0.0", "1.0.0") == 1

    def test_compare_patch(self) -> None:
        assert _compare_versions("1.0.1", "1.0.0") == 1

    def test_different_lengths_handled(self) -> None:
        # Shorter tuple is considered less than longer one with same prefix
        assert _compare_versions("1.0", "1.0.0") <= 0


class TestComponentVersion:
    """Tests for ComponentVersion data class."""

    def test_create(self) -> None:
        cv = ComponentVersion(
            component_id="python",
            component_type="cli",
            installed_version="3.11.0",
        )
        assert cv.component_id == "python"
        assert cv.installed_version == "3.11.0"
        assert cv.compatible is True

    def test_incompatible(self) -> None:
        cv = ComponentVersion(
            component_id="python",
            component_type="cli",
            installed_version="3.8.0",
            min_version="3.9.0",
            compatible=False,
        )
        assert cv.compatible is False
        assert cv.update_available is False

    def test_update_available(self) -> None:
        cv = ComponentVersion(
            component_id="python",
            component_type="cli",
            installed_version="3.8.0",
            latest_version="3.12.0",
            update_available=True,
        )
        assert cv.update_available is True

    def test_to_dict(self) -> None:
        cv = ComponentVersion(
            component_id="test", component_type="cli", installed_version="1.0.0"
        )
        d = cv.to_dict()
        assert d["component_id"] == "test"
        assert d["installed_version"] == "1.0.0"

    def test_from_dict(self) -> None:
        data = {
            "component_id": "python",
            "component_type": "cli",
            "installed_version": "3.11.0",
            "compatible": True,
        }
        cv = ComponentVersion.from_dict(data)
        assert cv.component_id == "python"
        assert cv.installed_version == "3.11.0"


class TestVersionManager:
    """Tests for VersionManager class."""

    def test_initial_state(self) -> None:
        event_bus = MagicMock()
        manager = VersionManager(event_bus=event_bus)
        assert manager.component_count == 0

    def test_register_version(self) -> None:
        event_bus = MagicMock()
        manager = VersionManager(event_bus=event_bus)
        cv = manager.register_version("python", "cli", "3.11.0")
        assert cv.component_id == "python"
        assert cv.installed_version == "3.11.0"
        assert manager.component_count == 1

    def test_register_version_publishes_event(self) -> None:
        event_bus = MagicMock()
        manager = VersionManager(event_bus=event_bus)
        manager.register_version("python", "cli", "3.11.0")
        assert event_bus.publish.called

    def test_get_version(self) -> None:
        event_bus = MagicMock()
        manager = VersionManager(event_bus=event_bus)
        manager.register_version("python", "cli", "3.11.0")
        cv = manager.get_version("python")
        assert cv is not None
        assert cv.installed_version == "3.11.0"

    def test_get_version_nonexistent(self) -> None:
        event_bus = MagicMock()
        manager = VersionManager(event_bus=event_bus)
        cv = manager.get_version("nonexistent")
        assert cv is None

    def test_check_compatibility(self) -> None:
        event_bus = MagicMock()
        manager = VersionManager(event_bus=event_bus)
        manager.register_version("python", "cli", "3.11.0")
        assert manager.check_compatibility("python") is True

    def test_check_compatibility_nonexistent(self) -> None:
        event_bus = MagicMock()
        manager = VersionManager(event_bus=event_bus)
        assert manager.check_compatibility("nonexistent") is True

    def test_set_min_version(self) -> None:
        event_bus = MagicMock()
        manager = VersionManager(event_bus=event_bus)
        manager.set_min_version("python", "3.10.0")
        assert manager.get_min_version("python") == "3.10.0"

    def test_default_min_versions(self) -> None:
        event_bus = MagicMock()
        manager = VersionManager(event_bus=event_bus)
        assert "python" in DEFAULT_MIN_VERSIONS

    def test_set_latest_version(self) -> None:
        event_bus = MagicMock()
        manager = VersionManager(event_bus=event_bus)
        manager.register_version("python", "cli", "3.11.0")
        manager.set_latest_version("python", "3.12.0")
        cv = manager.get_version("python")
        assert cv is not None
        assert cv.update_available is True

    def test_get_incompatible_components(self) -> None:
        event_bus = MagicMock()
        manager = VersionManager(event_bus=event_bus)
        manager.register_version("good", "cli", "3.11.0")
        manager.set_min_version("bad", "99.0.0")
        manager.register_version("bad", "cli", "1.0.0")
        incompatible = manager.get_incompatible_components()
        assert len(incompatible) == 1
        assert incompatible[0].component_id == "bad"

    def test_get_outdated_components(self) -> None:
        event_bus = MagicMock()
        manager = VersionManager(event_bus=event_bus)
        manager.register_version("tool", "cli", "1.0.0")
        manager.set_latest_version("tool", "2.0.0")
        outdated = manager.get_outdated_components()
        assert len(outdated) == 1

    def test_list_versions_by_type(self) -> None:
        event_bus = MagicMock()
        manager = VersionManager(event_bus=event_bus)
        manager.register_version("p1", "provider", "1.0.0")
        manager.register_version("p2", "provider", "2.0.0")
        manager.register_version("c1", "cli", "3.0.0")
        providers = manager.list_versions("provider")
        assert len(providers) == 2
        clis = manager.list_versions("cli")
        assert len(clis) == 1

    def test_save_and_load(self, tmp_path: Path) -> None:
        event_bus = MagicMock()
        versions_file = tmp_path / "versions.json"
        manager = VersionManager(event_bus=event_bus, versions_file=versions_file)
        manager.register_version("python", "cli", "3.11.0")
        manager.save()

        loaded = VersionManager(event_bus=event_bus, versions_file=versions_file)
        loaded.load()
        cv = loaded.get_version("python")
        assert cv is not None
        assert cv.installed_version == "3.11.0"

    def test_save_and_load_empty(self, tmp_path: Path) -> None:
        event_bus = MagicMock()
        versions_file = tmp_path / "versions.json"
        manager = VersionManager(event_bus=event_bus, versions_file=versions_file)
        manager.load()  # Should not raise
        assert manager.component_count == 0

    def test_no_event_bus(self) -> None:
        manager = VersionManager(event_bus=None)
        manager.register_version("test", "cli", "1.0.0")
        assert manager.component_count == 1
