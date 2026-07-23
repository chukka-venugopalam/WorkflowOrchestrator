"""SSH transport — secure shell communication interface.

This is an interface-only module. No SSH connections are established.
Implementations will be created in future phases.
"""

from __future__ import annotations

from abc import abstractmethod

from workflow_orchestrator.transports.transport import Transport, TransportRequest, TransportResponse


class SshTransport(Transport):
    """Abstract transport for SSH communication.

    Subclasses implement SSH connections via libraries like
    asyncssh or paramiko.
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
