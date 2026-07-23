"""MCP Manager — discovers MCP servers and registers their capabilities.

Supports:
- Filesystem
- Git
- GitHub
- Browser
- Database
- Any server implementing the MCP protocol
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


@dataclass
class McpServerInfo:
    """Information about a discovered MCP server.

    Attributes:
        name: Server name.
        command: CLI command to start the server.
        args: Arguments for the command.
        capabilities: Capabilities the server provides.
        transport: Transport type (stdio, sse, etc.).
        version: Server version.
    """

    name: str = ""
    command: str = ""
    args: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    transport: str = "stdio"
    version: str = ""
    available: bool = False


class McpManager:
    """Discovers MCP (Model Context Protocol) servers on the system.

    Scans for known MCP servers and parses their manifests to
    register capabilities with the Capability Registry.

    Usage:
        >>> mgr = McpManager()
        >>> servers = mgr.discover_all()
        >>> for s in servers:
        ...     print(f"{s.name}: {s.capabilities}")
    """

    # Known MCP servers: name -> (command, args, capabilities)
    _KNOWN_SERVERS: list[dict[str, Any]] = [
        {
            "name": "Filesystem",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"],
            "capabilities": ["tool.filesystem.read", "tool.filesystem.write", "tool.filesystem.search"],
            "transport": "stdio",
        },
        {
            "name": "Git",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-git"],
            "capabilities": ["tool.git.status", "tool.git.log", "tool.git.diff"],
            "transport": "stdio",
        },
        {
            "name": "GitHub",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "capabilities": ["tool.github.pr", "tool.github.issue", "tool.github.repo"],
            "transport": "stdio",
        },
        {
            "name": "Browser",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-browser"],
            "capabilities": ["tool.browser.navigate", "tool.browser.search"],
            "transport": "stdio",
        },
        {
            "name": "Database",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-database"],
            "capabilities": ["tool.database.query", "tool.database.schema"],
            "transport": "stdio",
        },
        {
            "name": "Memory",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"],
            "capabilities": ["tool.memory.store", "tool.memory.retrieve"],
            "transport": "stdio",
        },
        {
            "name": "Playwright",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-playwright"],
            "capabilities": ["tool.browser.screenshot", "tool.browser.click", "tool.browser.type"],
            "transport": "stdio",
        },
        {
            "name": "Sequential Thinking",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
            "capabilities": ["reasoning.sequential", "reasoning.structured"],
            "transport": "stdio",
        },
    ]

    def __init__(
        self,
        event_bus: EventBus | None = None,
        capability_registry: Any = None,
    ) -> None:
        """Initialize the MCP Manager.

        Args:
            event_bus: Optional EventBus for publishing events.
            capability_registry: Optional CapabilityRegistry for registration.
        """
        self._event_bus = event_bus
        self._capability_registry = capability_registry
        self._discovered_servers: dict[str, McpServerInfo] = {}

    def discover_all(self) -> list[McpServerInfo]:
        """Discover all MCP servers available on the system.

        Returns:
            List of McpServerInfo objects.
        """
        servers: list[McpServerInfo] = []
        for server_def in self._KNOWN_SERVERS:
            info = self._discover_server(server_def)
            if info.available:
                servers.append(info)
                self._discovered_servers[info.name] = info

                # Register capabilities
                if self._capability_registry is not None:
                    self._register_capabilities(info)

        logger.info("Discovered %d MCP servers", len(servers))
        return servers

    def _discover_server(self, server_def: dict[str, Any]) -> McpServerInfo:
        """Discover a specific MCP server.

        Args:
            server_def: Server definition dict.

        Returns:
            McpServerInfo for the discovered server.
        """
        command = server_def["command"]
        args = server_def["args"]

        # Check if the command is available
        if not shutil.which(command):
            return McpServerInfo(name=server_def["name"], available=False)

        # Try to verify the server is available
        available = False
        if command == "npx":
            # Check if it's npm-based MCP server (presence of npm)
            available = shutil.which("npm") is not None
        else:
            available = True

        return McpServerInfo(
            name=server_def["name"],
            command=command,
            args=args,
            capabilities=server_def["capabilities"],
            transport=server_def["transport"],
            available=available,
        )

    def _register_capabilities(self, info: McpServerInfo) -> None:
        """Register MCP server capabilities with the capability registry.

        Args:
            info: The MCP server info.
        """
        try:
            from workflow_orchestrator.core.capability_registry import (
                CapabilityManifest, CandidateHealth, CostTier, QualityLevel,
            )

            for cap_id in info.capabilities:
                manifest = CapabilityManifest(
                    id=cap_id,
                    name=f"MCP: {info.name} - {cap_id}",
                    description=f"Provided by MCP server: {info.name}",
                    provider_id=f"mcp.{info.name.lower()}",
                    version="1.0.0",
                    cost_tier=CostTier.LOW,
                    quality=QualityLevel.STABLE,
                    health=CandidateHealth.AVAILABLE,
                    tags=["mcp", info.name.lower()],
                )
                self._capability_registry.register(manifest)

            logger.debug("Registered %d capabilities for MCP server '%s'", len(info.capabilities), info.name)
        except Exception as exc:
            logger.warning("Failed to register MCP capabilities: %s", exc)

    def list_discovered(self) -> list[McpServerInfo]:
        """List all discovered MCP servers.

        Returns:
            List of McpServerInfo objects.
        """
        return list(self._discovered_servers.values())

    def get_server(self, name: str) -> McpServerInfo | None:
        """Get a discovered MCP server by name.

        Args:
            name: Server name.

        Returns:
            McpServerInfo or None.
        """
        return self._discovered_servers.get(name)
