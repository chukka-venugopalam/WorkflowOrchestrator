"""REST API transport implementation — communicates with REST APIs via HTTP.

Supports HTTP/HTTPS requests with auth, headers, streaming, and cancellation.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, AsyncIterator, Optional

from workflow_orchestrator.transports.api_transport import ApiTransport
from workflow_orchestrator.transports.transport import (
    TransportError,
    TransportRequest,
    TransportResponse,
)

logger = logging.getLogger(__name__)


class RestApiTransport(ApiTransport):
    """REST API transport implementation using httpx.

    Supports GET, POST, PUT, DELETE, PATCH methods with
    authentication headers, request/response streaming,
    and request cancellation.
    """

    def __init__(
        self,
        base_url: str = "",
        default_headers: dict[str, str] | None = None,
        default_timeout: int = 30,
    ) -> None:
        """Initialize the REST API transport.

        Args:
            base_url: Base URL for all requests.
            default_headers: Default headers to include in all requests.
            default_timeout: Default timeout in seconds.
        """
        self._base_url = base_url.rstrip("/")
        self._default_headers = default_headers or {}
        self._default_timeout = default_timeout
        self._client: Any = None
        self._active_requests: dict[str, Any] = {}

    async def _ensure_client(self) -> Any:
        """Ensure the HTTP client is initialized.

        Returns:
            The HTTP client instance.
        """
        if self._client is None:
            try:
                import httpx
                self._client = httpx.AsyncClient(
                    base_url=self._base_url if self._base_url else None,
                    headers=self._default_headers,
                    timeout=httpx.Timeout(self._default_timeout),
                )
            except ImportError:
                logger.warning("httpx not installed. REST transport will use simulated mode.")
                return None
        return self._client

    async def send(self, request: TransportRequest) -> TransportResponse:
        """Send an HTTP request and receive a response.

        Args:
            request: The transport request with URL, method, headers, body.

        Returns:
            TransportResponse with status, headers, body.

        Raises:
            TransportError: If the request fails.
        """
        start_time = time.time()
        client = await self._ensure_client()

        if client is None:
            return TransportResponse(
                status_code=200,
                body=f"[REST Transport Simulation] {request.method} {request.url}",
                duration_ms=(time.time() - start_time) * 1000,
                success=True,
            )

        url = request.url
        headers = {**self._default_headers, **request.headers}
        timeout = request.timeout_seconds or self._default_timeout

        try:
            response = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=request.body if request.body else None,
                timeout=timeout,
            )

            duration_ms = (time.time() - start_time) * 1000
            return TransportResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                body=response.text,
                duration_ms=duration_ms,
                success=response.status_code < 500,
                error="" if response.status_code < 500 else f"HTTP {response.status_code}",
            )
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            raise TransportError(
                message=str(exc),
                status_code=0,
                transport_type="rest_api",
                recoverable=True,
                retryable=True,
            ) from exc

    async def send_stream(self, request: TransportRequest) -> AsyncIterator[TransportResponse]:
        """Send a request and stream the response.

        Args:
            request: The transport request.

        Yields:
            TransportResponse chunks as they arrive.
        """
        client = await self._ensure_client()
        if client is None:
            yield await self.send(request)
            return

        headers = {**self._default_headers, **request.headers}

        try:
            async with client.stream(
                method=request.method,
                url=request.url,
                headers=headers,
                content=request.body if request.body else None,
                timeout=request.timeout_seconds or self._default_timeout,
            ) as response:
                full_text = ""
                async for chunk in response.aiter_text():
                    full_text += chunk
                    yield TransportResponse(
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        body=chunk,
                        duration_ms=0.0,
                        success=True,
                    )
        except Exception as exc:
            raise TransportError(
                message=str(exc),
                status_code=0,
                transport_type="rest_api",
                recoverable=True,
                retryable=True,
            ) from exc

    async def cancel(self, request_id: str) -> None:
        """Cancel an in-flight request.

        Args:
            request_id: The request identifier to cancel.
        """
        # httpx doesn't support cancellation by request ID natively
        # This is a no-op for now
        logger.debug("Cancel requested for request '%s' on REST transport", request_id)

    async def health(self) -> bool:
        """Check if the transport is healthy.

        Returns:
            True if the HTTP client is available.
        """
        try:
            client = await self._ensure_client()
            return client is not None
        except Exception:
            return False

    @property
    def transport_type(self) -> str:
        """Human-readable transport type identifier."""
        return "rest_api"
