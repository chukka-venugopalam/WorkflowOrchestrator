"""Tests for ToolDetector integration module."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from workflow_orchestrator.integrations.tool_detector import ToolDetector, ToolInfo


class TestToolInfo:
    """Tests for ToolInfo data class."""

    def test_create(self) -> None:
        tool = ToolInfo(name="git", category="vcs", available=True)
        assert tool.name == "git"
        assert tool.category == "vcs"
        assert tool.available is True

    def test_unavailable(self) -> None:
        tool = ToolInfo(name="docker", category="container", available=False)
        assert tool.available is False

    def test_with_all_fields(self) -> None:
        tool = ToolInfo(
            name="test", category="util", command="test",
            path="/usr/bin/test", version="1.0", available=True,
        )
        assert tool.name == "test"
        assert tool.path == "/usr/bin/test"
        assert tool.version == "1.0"


class TestToolDetector:
    """Tests for ToolDetector class."""

    def test_detect_returns_list(self) -> None:
        detector = ToolDetector()
        tools = detector.detect_all()
        assert isinstance(tools, list)

    @patch("shutil.which", return_value="/usr/bin/git")
    def test_detect_git(self, mock_which: MagicMock) -> None:
        detector = ToolDetector()
        tools = detector.detect_all()
        names = [t.name for t in tools if t.available]
        assert "Git" in names

    @patch("shutil.which", return_value="/usr/bin/docker")
    def test_detect_docker(self, mock_which: MagicMock) -> None:
        detector = ToolDetector()
        tools = detector.detect_all()
        names = [t.name for t in tools if t.available]
        assert "Docker" in names

    @patch("shutil.which", return_value="/usr/bin/code")
    def test_detect_vscode(self, mock_which: MagicMock) -> None:
        detector = ToolDetector()
        tools = detector.detect_all()
        names = [t.name for t in tools if t.available]
        assert "VS Code" in names

    @patch("shutil.which", return_value="/usr/bin/playwright")
    def test_detect_playwright(self, mock_which: MagicMock) -> None:
        detector = ToolDetector()
        tools = detector.detect_all()
        names = [t.name for t in tools if t.available]
        assert "Playwright" in names

    @patch("shutil.which", return_value="/usr/bin/ssh")
    def test_detect_ssh(self, mock_which: MagicMock) -> None:
        detector = ToolDetector()
        tools = detector.detect_all()
        names = [t.name for t in tools if t.available]
        assert "SSH" in names

    def test_no_tools(self) -> None:
        with patch("shutil.which", return_value=None):
            detector = ToolDetector()
            tools = detector.detect_all()
            available = [t for t in tools if t.available]
            assert len(available) == 0

    def test_detect_available(self) -> None:
        def which_side_effect(cmd: str) -> Optional[str]:
            return f"/usr/bin/{cmd}"

        with patch("shutil.which", side_effect=which_side_effect):
            detector = ToolDetector()
            tools = detector.detect_available()
            assert len(tools) > 0

    def test_path_based_detection(self) -> None:
        with patch("pathlib.Path.exists", return_value=True):
            with patch("shutil.which", return_value=None):
                detector = ToolDetector()
                tools = detector.detect_all()
                available = [t for t in tools if t.available]
                # Some tools should be found via path check
                assert len(available) > 0
