"""API transport — REST API communication interface.

This is an interface-only module. No HTTP calls are made.
Implementations will be created in future phases.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from workflow_orchestrator.transports.transport import Transport, TransportRequest, TransportResponse


class ApiTransport(Transport):
    """Abstract transport for REST API communication.

    Subclasses must implement send(), cancel(), and health().
    API-specific concerns like authentication, rate limiting,
    and retry logic are handled by subclasses.
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
