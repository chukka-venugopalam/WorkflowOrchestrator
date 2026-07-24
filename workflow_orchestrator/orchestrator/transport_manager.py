"""Transport Manager — auto-discovers and coordinates all transport channels.

Supports:
- REST API
- CLI Command
- Browser Automation
- Desktop Automation
- MCP Client
- SSH Command
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from workflow_orchestrator.runtime.transport_runtime import TransportRuntime
from workflow_orchestrator.integrations.transport_factory import TransportFactory
from workflow_orchestrator.transports.transport import Transport, TransportRequest, TransportResponse

logger = logging.getLogger(__name__)


@dataclass
class TransportChannelStatus:
    """Status of a transport channel."""

    name: str
    available: bool
    description: str
    supports_async: bool = True


class TransportManager:
    """Orchestrates transport discovery, multi-transport dispatching, and health checking."""

    SUPPORTED_TRANSPORTS = [
        ("rest_api", "HTTP/HTTPS REST API Communication"),
        ("cli", "Command-Line Subprocess Execution"),
        ("browser", "Browser Automation (Playwright/Chrome)"),
        ("desktop", "Desktop UI Automation"),
        ("mcp", "Model Context Protocol Client"),
        ("ssh", "Remote SSH Command Execution"),
    ]

    def __init__(
        self,
        transport_runtime: Optional[TransportRuntime] = None,
        transport_factory: Optional[TransportFactory] = None,
    ) -> None:
        self.runtime = transport_runtime or TransportRuntime()
        self.factory = transport_factory or TransportFactory()

    async def discover_transports(self) -> List[TransportChannelStatus]:
        """Auto-discover available transports and check their health."""
        statuses: List[TransportChannelStatus] = []

        for t_type, desc in self.SUPPORTED_TRANSPORTS:
            transport = self.factory.create(t_type)
            is_healthy = False
            if transport:
                try:
                    if hasattr(transport, "health"):
                        is_healthy = await transport.health()
                    else:
                        is_healthy = True
                except Exception as exc:
                    logger.debug("Health check failed for transport %s: %s", t_type, exc)
                    is_healthy = False

            statuses.append(TransportChannelStatus(name=t_type, available=is_healthy, description=desc))

        return statuses

    async def send_request(
        self,
        transport_type: str,
        request: TransportRequest,
        config: Optional[Dict[str, Any]] = None,
    ) -> TransportResponse:
        """Send a request via a specified transport type."""
        transport = self.factory.create(transport_type, config)
        if not transport:
            raise ValueError(f"Unknown or unsupported transport type: {transport_type}")

        return await transport.send(request)
