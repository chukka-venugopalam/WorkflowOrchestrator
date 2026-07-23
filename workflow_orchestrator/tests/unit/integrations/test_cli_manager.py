"""Tests for CliManager integration module."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from workflow_orchestrator.integrations.cli_manager import CliManager, CliToolInfo


class TestCliToolInfo:
    """Tests for CliToolInfo data class."""

    def test_create(self) -> None:
        tool = CliToolInfo(name="Python", command="python", available=True)
        assert tool.name == "Python"
        assert tool.command == "python"
        assert tool.available is True

    def test_with_version(self) -> None:
        tool = CliToolInfo(name="Python", command="python", available=True, version="3.11.0")
        assert tool.version == "3.11.0"

    def test_not_available(self) -> None:
        tool = CliToolInfo(name="nonexistent", command="nonexistent", available=False)
        assert tool.available is False
        assert tool.version == ""


class TestCliManager:
    """Tests for CliManager class."""

    def test_detect_returns_list(self) -> None:
        manager = CliManager()
        tools = manager.detect_all()
        assert isinstance(tools, list)

    @patch("shutil.which", return_value="/usr/bin/python3")
    def test_detect_python(self, mock_which: MagicMock) -> None:
        manager = CliManager()
        tools = manager.detect_all()
        names = [t.name for t in tools if t.available]
        assert "Python" in names

    @patch("shutil.which", return_value="/usr/bin/node")
    def test_detect_node(self, mock_which: MagicMock) -> None:
        manager = CliManager()
        tools = manager.detect_all()
        names = [t.name for t in tools if t.available]
        assert "Node.js" in names

    @patch("shutil.which", return_value="/usr/bin/git")
    def test_detect_git(self, mock_which: MagicMock) -> None:
        manager = CliManager()
        tools = manager.detect_all()
        names = [t.name for t in tools if t.available]
        assert "Git" in names

    @patch("shutil.which", return_value="/usr/bin/docker")
    def test_detect_docker(self, mock_which: MagicMock) -> None:
        manager = CliManager()
        tools = manager.detect_all()
        names = [t.name for t in tools if t.available]
        assert "Docker" in names

    @patch("shutil.which", return_value="/usr/bin/gh")
    def test_detect_github_cli(self, mock_which: MagicMock) -> None:
        manager = CliManager()
        tools = manager.detect_all()
        names = [t.name for t in tools if t.available]
        assert "GitHub CLI" in names

    @patch("shutil.which", return_value="/usr/local/bin/claude")
    def test_detect_claude_code(self, mock_which: MagicMock) -> None:
        manager = CliManager()
        tools = manager.detect_all()
        names = [t.name for t in tools if t.available]
        assert "Claude Code" in names

    @patch("shutil.which", return_value="/usr/local/bin/codex")
    def test_detect_codex(self, mock_which: MagicMock) -> None:
        manager = CliManager()
        tools = manager.detect_all()
        names = [t.name for t in tools if t.available]
        assert "Codex CLI" in names

    def test_no_tools(self) -> None:
        with patch("shutil.which", return_value=None):
            manager = CliManager()
            tools = manager.detect_all()
            available = [t for t in tools if t.available]
            assert len(available) == 0

    def test_is_available(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/python3"):
            manager = CliManager()
            assert manager.is_available("python") is True

    def test_is_not_available(self) -> None:
        with patch("shutil.which", return_value=None):
            manager = CliManager()
            assert manager.is_available("nonexistent") is False

    def test_find(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/git"):
            manager = CliManager()
            tool = manager.find("git")
            assert tool is not None
            assert tool.name == "git"

    def test_find_not_found(self) -> None:
        with patch("shutil.which", return_value=None):
            manager = CliManager()
            tool = manager.find("nonexistent")
            assert tool is None

    def test_detect_available(self) -> None:
        def which_side_effect(cmd: str) -> Optional[str]:
            paths = {"python3": "/usr/bin/python3", "git": "/usr/bin/git"}
            return paths.get(cmd)

        with patch("shutil.which", side_effect=which_side_effect):
            manager = CliManager()
            available = manager.detect_available()
            assert len(available) >= 2
