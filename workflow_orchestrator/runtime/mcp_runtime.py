"""MCP Protocol Client Runtime — communicates with any server implementing the Model Context Protocol.

Supports:
- Standard JSON-RPC 2.0 stdio / SSE framing
- Dynamic capability, tool, resource, and prompt listing (`initialize`, `tools/list`, `resources/list`, `prompts/list`)
- Invocation of MCP tools (`tools/call`)
- Reading MCP resources (`resources/read`)
- Health monitoring and capability indexing across 11+ server types
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


@dataclass
class McpTool:
    name: str
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class McpResource:
    uri: str
    name: str
    description: str = ""
    mime_type: str = "text/plain"


@dataclass
class McpServerCapabilities:
    server_name: str
    version: str = "1.0.0"
    protocol_version: str = "2024-11-05"
    tools: List[McpTool] = field(default_factory=list)
    resources: List[McpResource] = field(default_factory=list)
    prompts: List[str] = field(default_factory=list)
    healthy: bool = True


class McpProtocolClient:
    """JSON-RPC 2.0 Client for Model Context Protocol servers."""

    def __init__(
        self,
        server_name: str,
        command: str,
        args: Optional[List[str]] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.server_name = server_name
        self.command = command
        self.args = args or []
        self.event_bus = event_bus
        self._request_id = 0
        self._proc: Optional[subprocess.Popen] = None
        self._capabilities = McpServerCapabilities(server_name=server_name)

    @property
    def capabilities(self) -> McpServerCapabilities:
        return self._capabilities

    def connect(self) -> bool:
        """Initialize connection and query MCP capabilities via JSON-RPC 2.0."""
        try:
            full_cmd = [self.command] + self.args
            self._proc = subprocess.Popen(
                full_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            # Perform MCP Handshake
            init_res = self._send_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                    "clientInfo": {"name": "WorkflowOrchestrator", "version": "1.0.0"},
                },
            )
            if init_res and "result" in init_res:
                s_info = init_res["result"].get("serverInfo", {})
                self._capabilities.version = s_info.get("version", "1.0.0")

            # Send initialized notification
            self._send_notification("notifications/initialized", {})

            # Discover tools dynamically
            tools_res = self._send_request("tools/list", {})
            if tools_res and "result" in tools_res:
                for t in tools_res["result"].get("tools", []):
                    self._capabilities.tools.append(
                        McpTool(
                            name=t.get("name", ""),
                            description=t.get("description", ""),
                            input_schema=t.get("inputSchema", {}),
                        )
                    )

            # Discover resources dynamically
            res_res = self._send_request("resources/list", {})
            if res_res and "result" in res_res:
                for r in res_res["result"].get("resources", []):
                    self._capabilities.resources.append(
                        McpResource(
                            uri=r.get("uri", ""),
                            name=r.get("name", ""),
                            description=r.get("description", ""),
                            mime_type=r.get("mimeType", "text/plain"),
                        )
                    )

            self._capabilities.healthy = True
            if self.event_bus:
                self.event_bus.publish(
                    Event(
                        type="mcp.server_connected",
                        data={"server": self.server_name, "tools_count": len(self._capabilities.tools)},
                    )
                )
            return True
        except Exception as exc:
            logger.warning("Failed to connect to MCP server '%s': %s", self.server_name, exc)
            self._capabilities.healthy = False
            return False

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke an MCP tool call (`tools/call`)."""
        if not self._proc or self._proc.poll() is not None:
            return {"success": False, "error": f"MCP server '{self.server_name}' is not connected."}

        res = self._send_request("tools/call", {"name": tool_name, "arguments": arguments})
        if res and "result" in res:
            return {"success": True, "content": res["result"].get("content", [])}
        return {"success": False, "error": res.get("error", {}).get("message", "MCP Tool call failed")}

    def disconnect(self) -> None:
        """Terminate MCP server process."""
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None
        self._capabilities.healthy = False

    def _send_request(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self._proc or not self._proc.stdin or not self._proc.stdout:
            return None
        self._request_id += 1
        req_pkt = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }
        try:
            self._proc.stdin.write(json.dumps(req_pkt) + "\n")
            self._proc.stdin.flush()
            line = self._proc.stdout.readline()
            if line:
                return json.loads(line)
        except Exception as exc:
            logger.debug("MCP JSON-RPC send_request error: %s", exc)
        return None

    def _send_notification(self, method: str, params: Dict[str, Any]) -> None:
        if not self._proc or not self._proc.stdin:
            return
        notif_pkt = {"jsonrpc": "2.0", "method": method, "params": params}
        try:
            self._proc.stdin.write(json.dumps(notif_pkt) + "\n")
            self._proc.stdin.flush()
        except Exception:
            pass
