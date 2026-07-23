"""Transport layer — abstract interfaces and concrete implementations.

This package defines transport interfaces and their implementations
for different communication protocols.

All transports are:
- Provider-agnostic
- Async-capable
- Error-typed
- Interchangeable
"""

from __future__ import annotations

from workflow_orchestrator.transports.transport import (
    Transport,
    TransportRequest,
    TransportResponse,
    TransportError,
    TransportStatus,
)
from workflow_orchestrator.transports.rest_api_transport import RestApiTransport
from workflow_orchestrator.transports.cli_command_transport import CliCommandTransport
from workflow_orchestrator.transports.browser_automation_transport import BrowserAutomationTransport
from workflow_orchestrator.transports.desktop_automation_transport import DesktopAutomationTransport
from workflow_orchestrator.transports.mcp_client_transport import McpClientTransport
from workflow_orchestrator.transports.ssh_command_transport import SshCommandTransport

__all__ = [
    "Transport",
    "TransportRequest",
    "TransportResponse",
    "TransportError",
    "TransportStatus",
    "RestApiTransport",
    "CliCommandTransport",
    "BrowserAutomationTransport",
    "DesktopAutomationTransport",
    "McpClientTransport",
    "SshCommandTransport",
]
