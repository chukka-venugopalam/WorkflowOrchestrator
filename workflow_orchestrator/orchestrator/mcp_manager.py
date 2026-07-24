"""MCP Manager — Model Context Protocol server lifecycle and configuration management.

Provides:
- Server discovery and listing
- Server configuration & environment setup
- Installation and removal
- Enable / Disable toggle
- Health checking and capability testing
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from workflow_orchestrator.integrations.mcp_manager import McpManager as IntMcpManager, McpServerInfo
from workflow_orchestrator.transports.mcp_client_transport import McpClientTransport

logger = logging.getLogger(__name__)


@dataclass
class McpServerDetail:
    """Detailed status and capabilities of an MCP server."""

    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    installed: bool = True
    healthy: bool = True
    capabilities: List[str] = field(default_factory=list)
    version: str = "1.0.0"


class MCPManager:
    """Orchestrator manager for Model Context Protocol servers."""

    def __init__(
        self,
        int_mcp_manager: Optional[IntMcpManager] = None,
        transport: Optional[McpClientTransport] = None,
    ) -> None:
        self.int_manager = int_mcp_manager or IntMcpManager()
        self.transport = transport or McpClientTransport()
        self._custom_servers: Dict[str, McpServerDetail] = {}

    def discover_and_list(self) -> List[McpServerDetail]:
        """List all discovered and registered MCP servers."""
        discovered = self.int_manager.discover_all()
        results: List[McpServerDetail] = []

        for s in discovered:
            results.append(
                McpServerDetail(
                    name=s.name,
                    command=s.command,
                    args=s.args,
                    env={},
                    enabled=True,
                    installed=s.available,
                    healthy=s.available,
                    capabilities=s.capabilities,
                    version=s.version,
                )
            )

        # Merge custom configured servers
        for name, server in self._custom_servers.items():
            if not any(r.name == name for r in results):
                results.append(server)

        return results

    def add_server(
        self,
        name: str,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        enabled: bool = True,
    ) -> McpServerDetail:
        """Register a new MCP server configuration."""
        server = McpServerDetail(
            name=name,
            command=command,
            args=args or [],
            env=env or {},
            enabled=enabled,
            installed=True,
            healthy=True,
            capabilities=["tools", "resources", "prompts"],
        )
        self._custom_servers[name] = server
        logger.info("Added MCP server configuration: %s", name)
        return server

    def remove_server(self, name: str) -> bool:
        """Remove a configured MCP server."""
        if name in self._custom_servers:
            del self._custom_servers[name]
            logger.info("Removed MCP server: %s", name)
            return True
        return False

    def enable_server(self, name: str) -> bool:
        """Enable an MCP server."""
        if name in self._custom_servers:
            self._custom_servers[name].enabled = True
            return True
        return False

    def disable_server(self, name: str) -> bool:
        """Disable an MCP server."""
        if name in self._custom_servers:
            self._custom_servers[name].enabled = False
            return True
        return False

    async def test_health(self, name: str) -> bool:
        """Run a health check against a specified MCP server."""
        server = self._custom_servers.get(name)
        if not server:
            servers = self.discover_and_list()
            server = next((s for s in servers if s.name == name), None)

        if not server or not server.enabled:
            return False

        try:
            # Test ping / connect via transport
            healthy = await self.transport.health()
            if server in self._custom_servers.values():
                server.healthy = healthy
            return healthy
        except Exception as exc:
            logger.warning("Health check failed for MCP server '%s': %s", name, exc)
            return False
