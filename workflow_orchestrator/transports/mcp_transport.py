"""MCP transport — Model Context Protocol communication interface.

This is an interface-only module. No MCP connections are established.
Implementations will be created in future phases.
"""

from __future__ import annotations

from abc import abstractmethod

from workflow_orchestrator.transports.transport import Transport, TransportRequest, TransportResponse


class McpTransport(Transport):
    """Abstract transport for Model Context Protocol (MCP) communication.

    MCP enables standardized communication between AI models and tools/services.
    Subclasses implement the MCP protocol for specific backends.
    """

    @abstractmethod
    async def send(self, request: TransportRequest) -> TransportResponse:
        ...

    @abstractmethod
    async def cancel(self, request_id: str) -> None:
        ...

    @abstractmethod
    async def health(self) -> bool:
        ...
