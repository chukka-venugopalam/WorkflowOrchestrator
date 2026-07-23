"""Browser transport — browser automation communication interface.

This is an interface-only module. No browser automation is performed.
Implementations will be created in future phases.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Optional

from workflow_orchestrator.transports.transport import Transport, TransportRequest, TransportResponse


class BrowserTransport(Transport):
    """Abstract transport for browser automation.

    Subclasses implement browser control via protocols like
    Playwright, Puppeteer, or Selenium.
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
