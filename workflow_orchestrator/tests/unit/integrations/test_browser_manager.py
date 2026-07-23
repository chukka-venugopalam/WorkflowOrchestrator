"""Tests for BrowserManager integration module."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from workflow_orchestrator.integrations.browser_manager import BrowserInfo, BrowserManager


class TestBrowserInfo:
    """Tests for BrowserInfo data class."""

    def test_create(self) -> None:
        info = BrowserInfo(name="Chrome", executable_path="/usr/bin/google-chrome", version="120.0")
        assert info.name == "Chrome"
        assert info.executable_path == "/usr/bin/google-chrome"
        assert info.version == "120.0"
        assert info.profiles == []

    def test_with_profiles(self) -> None:
        info = BrowserInfo(
            name="Chrome",
            executable_path="/usr/bin/google-chrome",
            profiles=["Default", "Profile 1"],
            running=True,
        )
        assert info.profiles == ["Default", "Profile 1"]
        assert info.running is True


class TestBrowserManager:
    """Tests for BrowserManager class."""

    @patch("shutil.which", return_value="/usr/bin/google-chrome")
    def test_detect_chrome(self, mock_which: MagicMock) -> None:
        with patch.object(BrowserManager, '_detect_profiles', return_value=None):
            with patch("shutil.which", return_value="/usr/bin/google-chrome"):
                manager = BrowserManager()
                browsers = manager.detect_all()
                names = [b.name for b in browsers]
                assert "Chrome" in names

    @patch("shutil.which", return_value="/usr/bin/firefox")
    def test_detect_firefox(self, mock_which: MagicMock) -> None:
        with patch.object(BrowserManager, '_detect_profiles', return_value=None):
            with patch("shutil.which", return_value="/usr/bin/firefox"):
                manager = BrowserManager()
                browsers = manager.detect_all()
                names = [b.name for b in browsers]
                assert "Firefox" in names

    def test_no_browsers_detected(self) -> None:
        with patch("shutil.which", return_value=None):
            with patch("pathlib.Path.exists", return_value=False):
                manager = BrowserManager()
                browsers = manager.detect_all()
                assert len(browsers) == 0

    @patch("shutil.which", return_value="/usr/bin/google-chrome")
    def test_find_executable(self, mock_which: MagicMock) -> None:
        manager = BrowserManager()
        path = manager.find_executable("Chrome")
        assert path is not None
        assert "chrome" in path.lower()

    def test_find_executable_not_found(self) -> None:
        with patch("shutil.which", return_value=None):
            manager = BrowserManager()
            path = manager.find_executable("Nonexistent")
            assert path is None

    def test_detect_brave(self) -> None:
        with patch.object(BrowserManager, '_detect_profiles', return_value=None):
            with patch("shutil.which", return_value="/usr/bin/brave-browser"):
                manager = BrowserManager()
                browsers = manager.detect_all()
                names = [b.name for b in browsers]
                assert "Brave" in names

    def test_detect_edge(self) -> None:
        with patch.object(BrowserManager, '_detect_profiles', return_value=None):
            with patch("shutil.which", return_value="/usr/bin/microsoft-edge"):
                manager = BrowserManager()
                browsers = manager.detect_all()
                names = [b.name for b in browsers]
                assert "Edge" in names
