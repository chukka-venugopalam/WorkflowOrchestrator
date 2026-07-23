"""Tests for DesktopManager integration module."""

from __future__ import annotations

from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from workflow_orchestrator.integrations.desktop_manager import DesktopAppInfo, DesktopManager


class TestDesktopAppInfo:
    """Tests for DesktopAppInfo data class."""

    def test_create(self) -> None:
        info = DesktopAppInfo(
            name="Claude Desktop",
            executable_path="/Applications/Claude.app",
        )
        assert info.name == "Claude Desktop"
        assert info.executable_path == "/Applications/Claude.app"

    def test_with_version(self) -> None:
        info = DesktopAppInfo(
            name="VS Code", executable_path="/usr/bin/code", version="1.85.0"
        )
        assert info.version == "1.85.0"


class TestDesktopManager:
    """Tests for DesktopManager class."""

    def test_detect_returns_list(self) -> None:
        manager = DesktopManager()
        apps = manager.detect_all()
        assert isinstance(apps, list)

    @patch("shutil.which", return_value="/usr/bin/code")
    def test_detect_vscode(self, mock_which: MagicMock) -> None:
        with patch("pathlib.Path.exists", return_value=False):
            manager = DesktopManager()
            apps = manager.detect_all()
            names = [a.name for a in apps]
            assert "VS Code" in names

    @patch("shutil.which", return_value="/usr/local/bin/claude")
    def test_detect_claude_desktop(self, mock_which: MagicMock) -> None:
        with patch("pathlib.Path.exists", return_value=False):
            manager = DesktopManager()
            apps = manager.detect_all()
            names = [a.name for a in apps]
            assert "Claude Desktop" in names

    @patch("shutil.which", return_value="/usr/bin/cursor")
    def test_detect_cursor(self, mock_which: MagicMock) -> None:
        with patch("pathlib.Path.exists", return_value=False):
            manager = DesktopManager()
            apps = manager.detect_all()
            names = [a.name for a in apps]
            assert "Cursor" in names

    def test_no_apps(self) -> None:
        with patch("shutil.which", return_value=None):
            with patch("pathlib.Path.exists", return_value=False):
                manager = DesktopManager()
                apps = manager.detect_all()
                names = [a.name for a in apps]
                assert isinstance(names, list)
