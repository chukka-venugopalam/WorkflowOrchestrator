"""Desktop transport — desktop automation communication interface.

This is an interface-only module. No desktop automation is performed.
Implementations will be created in future phases.
"""

from __future__ import annotations

from abc import abstractmethod

from workflow_orchestrator.transports.transport import Transport, TransportRequest, TransportResponse


class DesktopTransport(Transport):
    """Abstract transport for desktop automation.

    Subclasses implement desktop control via protocols like
    AppleScript, Windows COM, or X11 automation.
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
