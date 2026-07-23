"""Tests for McpManager integration module."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Generator, Optional
from unittest.mock import MagicMock, patch

import pytest

from workflow_orchestrator.integrations.mcp_manager import McpManager, McpServerInfo


class TestMcpServerInfo:
    """Tests for McpServerInfo data class."""

    def test_create(self) -> None:
        info = McpServerInfo(
            name="filesystem",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem"],
        )
        assert info.name == "filesystem"
        assert info.command == "npx"
        assert info.capabilities == []

    def test_with_capabilities(self) -> None:
        info = McpServerInfo(
            name="git",
            command="npx", args=["-y", "@modelcontextprotocol/server-git"],
            capabilities=["tool.git.status", "tool.git.log"],
        )
        assert len(info.capabilities) == 2


class TestMcpManager:
    """Tests for McpManager class."""

    def test_initial_state(self) -> None:
        event_bus = MagicMock()
        manager = McpManager(event_bus=event_bus)
        assert manager.list_discovered() == []

    def test_known_servers_in_discover(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/npx"):
            with patch("shutil.which") as mock_which:
                mock_which.side_effect = lambda cmd: "/usr/bin/npx" if cmd in ("npx", "npm") else None
                event_bus = MagicMock()
                manager = McpManager(event_bus=event_bus)
                servers = manager.discover_all()
                assert len(servers) > 0
                names = [s.name for s in servers]
                assert "Filesystem" in names

    def test_discover_no_npm(self) -> None:
        with patch("shutil.which", return_value=None):
            event_bus = MagicMock()
            manager = McpManager(event_bus=event_bus)
            servers = manager.discover_all()
            # No servers should be available without npm
            available = [s for s in servers if s.available]
            assert len(available) == 0

    def test_list_discovered(self) -> None:
        event_bus = MagicMock()
        manager = McpManager(event_bus=event_bus)
        with patch("shutil.which", return_value="/usr/bin/npx"):
            with patch("shutil.which") as mock_which:
                mock_which.side_effect = lambda cmd: "/usr/bin/npx" if cmd in ("npx", "npm") else None
                manager.discover_all()
                servers = manager.list_discovered()
                assert len(servers) > 0

    def test_get_server(self) -> None:
        event_bus = MagicMock()
        manager = McpManager(event_bus=event_bus)
        with patch("shutil.which", return_value="/usr/bin/npx"):
            with patch("shutil.which") as mock_which:
                mock_which.side_effect = lambda cmd: "/usr/bin/npx" if cmd in ("npx", "npm") else None
                manager.discover_all()
                server = manager.get_server("Filesystem")
                assert server is not None
                assert server.name == "Filesystem"

    def test_get_server_nonexistent(self) -> None:
        event_bus = MagicMock()
        manager = McpManager(event_bus=event_bus)
        server = manager.get_server("nonexistent")
        assert server is None
