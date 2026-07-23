"""CLI transport — command-line execution communication interface.

This is an interface-only module. No CLI commands are executed.
Implementations will be created in future phases.
"""

from __future__ import annotations

from abc import abstractmethod

from workflow_orchestrator.transports.transport import Transport, TransportRequest, TransportResponse


class CliTransport(Transport):
    """Abstract transport for CLI command execution.

    Subclasses implement command execution via subprocess,
    SSH, or container exec.
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
