"""Abstract transport interface for provider communication.

All provider adapters communicate through a Transport layer.
This abstract interface defines the contract for all transport
implementations.

No transport implementations exist in this package — only interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Optional


class TransportStatus(Enum):
    """Status of a transport operation."""

    PENDING = "pending"
    IN_FLIGHT = "in_flight"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TransportRequest:
    """A request to send through a transport.

    Attributes:
        url: Target URL or endpoint.
        method: HTTP method or transport-specific action.
        headers: Request headers.
        body: Request body content.
        timeout_seconds: Maximum time to wait.
        metadata: Additional transport metadata.
    """

    url: str = ""
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    body: str = ""
    timeout_seconds: int = 30
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TransportResponse:
    """A response received through a transport.

    Attributes:
        status_code: Status code (transport-specific).
        headers: Response headers.
        body: Response body content.
        duration_ms: Round-trip duration in milliseconds.
        success: Whether the request succeeded.
        error: Error details if failed.
    """

    status_code: int = 200
    headers: dict[str, str] = field(default_factory=dict)
    body: str = ""
    duration_ms: float = 0.0
    success: bool = True
    error: str = ""


class TransportError(Exception):
    """A typed error from a transport operation.

    Attributes:
        message: Human-readable error message.
        status_code: Associated status code.
        transport_type: Which transport produced the error.
        recoverable: Whether the error is recoverable.
        retryable: Whether the operation can be retried.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        transport_type: str = "unknown",
        recoverable: bool = False,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.transport_type = transport_type
        self.recoverable = recoverable
        self.retryable = retryable


class Transport(ABC):
    """Abstract transport interface for provider communication.

    All transports must implement:
    - send(): Send a request and receive a response
    - send_stream(): Send a request and stream the response
    - cancel(): Cancel an in-flight request

    Usage:
        >>> transport = SomeTransport()
        >>> response = await transport.send(
        ...     TransportRequest(url="https://api.example.com", method="POST")
        ... )
        >>> print(response.body)
    """

    @abstractmethod
    async def send(self, request: TransportRequest) -> TransportResponse:
        """Send a request and receive a response.

        Args:
            request: The transport request.

        Returns:
            A TransportResponse.

        Raises:
            TransportError: If the transport fails.
        """
        ...

    async def send_stream(
        self,
        request: TransportRequest,
    ) -> AsyncIterator[TransportResponse]:
        """Send a request and stream the response.

        Args:
            request: The transport request.

        Yields:
            TransportResponse chunks as they arrive.
        """
        # Default: non-streaming fallback
        response = await self.send(request)
        yield response

    @abstractmethod
    async def cancel(self, request_id: str) -> None:
        """Cancel an in-flight request.

        Args:
            request_id: The request identifier to cancel.
        """
        ...

    @abstractmethod
    async def health(self) -> bool:
        """Check if the transport is healthy and operational.

        Returns:
            True if the transport is healthy.
        """
        ...

    @property
    def transport_type(self) -> str:
        """Human-readable transport type identifier."""
        return self.__class__.__name__.replace("Transport", "").lower()
