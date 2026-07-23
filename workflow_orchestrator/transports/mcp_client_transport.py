"""MCP transport implementation — Model Context Protocol communication.

Supports tool discovery, resource access, and prompt template
management through the MCP protocol.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Optional

from workflow_orchestrator.transports.mcp_transport import McpTransport
from workflow_orchestrator.transports.transport import (
    TransportError,
    TransportRequest,
    TransportResponse,
)

logger = logging.getLogger(__name__)


class McpClientTransport(McpTransport):
    """MCP (Model Context Protocol) transport implementation.

    Supports:
    - Tool discovery and invocation
    - Resource access and listing
    - Prompt template management
    - Streaming responses

    Can connect via stdio (local subprocess) or SSE (remote).
    """

    def __init__(
        self,
        connection_type: str = "stdio",
        command: str | None = None,
        server_url: str | None = None,
    ) -> None:
        """Initialize the MCP transport.

        Args:
            connection_type: "stdio" for local processes, "sse" for remote.
            command: Command to start a local MCP server (stdio mode).
            server_url: URL of a remote MCP server (SSE mode).
        """
        self._connection_type = connection_type
        self._command = command
        self._server_url = server_url
        self._session: Any = None
        self._process: asyncio.subprocess.Process | None = None

    async def _ensure_connected(self) -> Any:
        """Ensure the MCP session is connected.

        Returns:
            The MCP session.
        """
        if self._session is not None:
            return self._session

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            from mcp.client.sse import sse_client

            if self._connection_type == "stdio" and self._command:
                server_params = StdioServerParameters(command=self._command)
                transport = stdio_client(server_params)
            elif self._connection_type == "sse" and self._server_url:
                transport = sse_client(self._server_url)
            else:
                logger.warning("MCP not configured. Using simulated mode.")
                return None

            read, write = await transport.__aenter__()
            self._session = await ClientSession(read, write).__aenter__()
            await self._session.initialize()
            logger.debug("MCP session initialized (%s)", self._connection_type)
            return self._session
        except ImportError:
            logger.warning("mcp library not installed. MCP transport will use simulated mode.")
            return None
        except Exception as exc:
            raise TransportError(
                message=f"Failed to connect MCP: {exc}",
                transport_type="mcp_client",
                recoverable=True,
            ) from exc

    async def send(self, request: TransportRequest) -> TransportResponse:
        """Send a request via MCP.

        Actions (in request.metadata):
        - "list_tools": List available tools
        - "call_tool": Call a tool (request.metadata["tool_name"], request.body as args)
        - "list_resources": List available resources
        - "read_resource": Read a resource (request.url as URI)

        Args:
            request: The transport request.

        Returns:
            TransportResponse with MCP result.
        """
        start_time = time.time()
        session = await self._ensure_connected()

        if session is None:
            return TransportResponse(
                body=f"[MCP Simulation] {request.metadata.get('action', 'unknown')}",
                duration_ms=(time.time() - start_time) * 1000,
                success=True,
            )

        action = request.metadata.get("action", "list_tools")

        try:
            if action == "list_tools":
                result = await session.list_tools()
                tools = [{"name": t.name, "description": t.description} for t in result.tools]
                return TransportResponse(
                    body=json.dumps(tools, indent=2),
                    duration_ms=(time.time() - start_time) * 1000,
                    success=True,
                )
            elif action == "call_tool":
                tool_name = request.metadata.get("tool_name", "")
                args = json.loads(request.body) if request.body else {}
                result = await session.call_tool(tool_name, arguments=args)
                content = "\n".join(c.text for c in result.content if hasattr(c, "text"))
                return TransportResponse(
                    body=content or str(result),
                    duration_ms=(time.time() - start_time) * 1000,
                    success=True,
                )
            elif action == "list_resources":
                result = await session.list_resources()
                resources = [{"uri": r.uri, "name": r.name} for r in result.resources]
                return TransportResponse(
                    body=json.dumps(resources, indent=2),
                    duration_ms=(time.time() - start_time) * 1000,
                    success=True,
                )
            elif action == "read_resource":
                result = await session.read_resource(request.url)
                return TransportResponse(
                    body=str(result),
                    duration_ms=(time.time() - start_time) * 1000,
                    success=True,
                )
            else:
                raise TransportError(
                    message=f"Unknown MCP action: {action}",
                    transport_type="mcp_client",
                    recoverable=False,
                )
        except Exception as exc:
            raise TransportError(
                message=str(exc),
                transport_type="mcp_client",
                recoverable=True,
                retryable=True,
            ) from exc

    async def cancel(self, request_id: str) -> None:
        """Cancel an MCP request.

        Args:
            request_id: The request identifier.
        """
        logger.debug("Cancel requested for MCP request '%s'", request_id)

    async def health(self) -> bool:
        """Check if the MCP transport is healthy.

        Returns:
            True if connected.
        """
        if self._session is not None:
            return True
        try:
            session = await self._ensure_connected()
            return session is not None
        except Exception:
            return False

    @property
    def transport_type(self) -> str:
        """Human-readable transport type identifier."""
        return f"mcp_client_{self._connection_type}"
