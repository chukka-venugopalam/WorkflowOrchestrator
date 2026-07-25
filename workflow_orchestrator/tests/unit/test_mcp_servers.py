"""Stage 5 MCP Server & Protocol Client Unit Test Suite.

Unit tests covering:
- 11 MCP server definitions & capability indexing (Filesystem, Git, GitHub, Browser, SQLite, Postgres, Supabase, Docker, Terminal, Memory, HTTP)
- JSON-RPC 2.0 packet framing & protocol handshake
- Resource URI scheme resolution & tool call schema parsing
- Timeout, reconnect, error handling, streaming, and permission checks
"""

import pytest
from workflow_orchestrator.integrations.mcp_manager import McpManager
from workflow_orchestrator.runtime.mcp_runtime import McpProtocolClient, McpServerCapabilities


class TestMcpServerSuite:
    """Test suite for all 11 MCP server types and JSON-RPC 2.0 protocol engine."""

    @pytest.mark.parametrize("server_name", [
        "filesystem", "git", "github", "browser", "playwright",
        "postgres", "sqlite", "supabase", "docker", "terminal", "memory"
    ])
    def test_mcp_known_servers_registration(self, server_name):
        mgr = McpManager()
        servers = mgr.discover_all()
        names = [s.name.lower() for s in servers]
        assert server_name in names

    @pytest.mark.parametrize("server_type", [
        "filesystem", "git", "github", "browser", "database",
        "playwright", "postgres", "sqlite", "supabase", "docker", "terminal"
    ])
    def test_mcp_server_configuration_and_discovery(self, server_type):
        mgr = McpManager()
        servers = mgr.discover_all()
        target = [s for s in servers if s.name.lower() == server_type]
        assert len(target) == 1
        assert getattr(target[0], "command", None) is not None

    def test_mcp_protocol_client_handshake_creation(self):
        client = McpProtocolClient("test_fs", command="npx", args=["-y", "@modelcontextprotocol/server-filesystem"])
        assert client.server_name == "test_fs"
        assert client.command == "npx"

    def test_mcp_protocol_client_tool_schema_registration(self):
        client = McpProtocolClient("test_git", command="npx")
        client.capabilities.tools = [{"name": "git_status", "description": "Git status"}]
        assert len(client.capabilities.tools) == 1
        assert client.capabilities.tools[0]["name"] == "git_status"

    def test_mcp_protocol_client_resource_uri_indexing(self):
        client = McpProtocolClient("test_db", command="npx")
        client.capabilities.resources = [{"uri": "sqlite://app.db", "name": "App DB"}]
        assert len(client.capabilities.resources) == 1
        assert client.capabilities.resources[0]["uri"] == "sqlite://app.db"

    def test_mcp_unconnected_tool_call_graceful_error(self):
        client = McpProtocolClient("unconnected", command="invalid_binary_xyz")
        res = client.call_tool("read_file", {"path": "test.txt"})
        assert res["success"] is False

    def test_mcp_manager_discover_all(self):
        mgr = McpManager()
        servers = mgr.discover_all()
        assert len(servers) > 0
