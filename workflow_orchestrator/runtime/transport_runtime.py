"""Transport Runtime — manages transport lifecycle, connection pooling, and routing.

Coordinates transport selection based on provider/agent requirements,
manages connection lifecycle, and provides unified send/receive interface.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Optional

from workflow_orchestrator.transports.transport import (
    Transport,
    TransportRequest,
    TransportResponse,
)

logger = logging.getLogger(__name__)


class TransportRuntime:
    """Runtime orchestrator for transport lifecycle and communication.

    Manages multiple transport implementations, provides connection
    pooling, health checking, and unified send/receive interface.

    Usage:
        >>> runtime = TransportRuntime()
        >>> runtime.register("rest_api", rest_transport)
        >>> response = await runtime.send("rest_api", request)
    """

    def __init__(self, event_bus: Any = None) -> None:
        """Initialize the Transport Runtime.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._transports: dict[str, Transport] = {}
        self._event_bus = event_bus

    @property
    def transports(self) -> dict[str, Transport]:
        """All registered transports."""
        return dict(self._transports)

    def list_transport_types(self) -> list[str]:
        """List all registered transport type names.

        Returns:
            Sorted list of transport type names.
        """
        return sorted(self._transports.keys())

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, name: str, transport: Transport, overwrite: bool = False) -> None:
        """Register a transport implementation.

        Args:
            name: Identifier for this transport.
            transport: Transport instance.
            overwrite: If True, replace an existing transport.
        """
        if name in self._transports and not overwrite:
            logger.warning("Transport '%s' already registered, skipping", name)
            return

        self._transports[name] = transport
        logger.debug("Registered transport '%s' (%s)", name, transport.transport_type)

    def unregister(self, name: str) -> None:
        """Unregister a transport.

        Args:
            name: Transport identifier to remove.
        """
        self._transports.pop(name, None)

    def get(self, name: str) -> Transport | None:
        """Get a registered transport by name.

        Args:
            name: Transport identifier.

        Returns:
            Transport instance, or None if not found.
        """
        return self._transports.get(name)

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self, transport_name: str) -> bool:
        """Connect a transport.

        Args:
            transport_name: Transport identifier.

        Returns:
            True if connected successfully.
        """
        transport = self._transports.get(transport_name)
        if transport is None:
            return False

        try:
            healthy = await transport.health()
            if healthy:
                self._publish_event("transport.connected", {
                    "transport": transport_name,
                    "type": transport.transport_type,
                })
                return True
            return False
        except Exception as exc:
            logger.warning("Failed to connect transport '%s': %s", transport_name, exc)
            self._publish_event("transport.connection_failed", {
                "transport": transport_name,
                "error": str(exc),
            })
            return False

    async def disconnect(self, transport_name: str) -> bool:
        """Disconnect a transport.

        Args:
            transport_name: Transport identifier.

        Returns:
            True if disconnected successfully.
        """
        transport = self._transports.get(transport_name)
        if transport is None:
            return False

        # Call disconnect if available
        if hasattr(transport, "disconnect"):
            try:
                await transport.disconnect()  # type: ignore[union-attr]
            except Exception:
                pass

        self._publish_event("transport.disconnected", {
            "transport": transport_name,
        })
        return True

    # ------------------------------------------------------------------
    # Communication
    # ------------------------------------------------------------------

    async def send(
        self,
        transport_name: str,
        request: TransportRequest,
    ) -> TransportResponse:
        """Send a request through a transport.

        Args:
            transport_name: Transport to use.
            request: The transport request.

        Returns:
            TransportResponse.

        Raises:
            KeyError: If the transport is not registered.
        """
        transport = self._transports.get(transport_name)
        if transport is None:
            raise KeyError(f"Transport '{transport_name}' not registered. Available: {list(self._transports.keys())}")

        try:
            response = await transport.send(request)
            return response
        except Exception:
            raise

    async def send_stream(
        self,
        transport_name: str,
        request: TransportRequest,
    ) -> AsyncIterator[TransportResponse]:
        """Send a request and stream the response.

        Args:
            transport_name: Transport to use.
            request: The transport request.

        Yields:
            TransportResponse chunks.

        Raises:
            KeyError: If the transport is not registered.
        """
        transport = self._transports.get(transport_name)
        if transport is None:
            raise KeyError(f"Transport '{transport_name}' not registered.")

        async for chunk in transport.send_stream(request):
            yield chunk

    async def cancel(self, transport_name: str, request_id: str) -> None:
        """Cancel an in-flight request on a transport.

        Args:
            transport_name: Transport to use.
            request_id: Request identifier to cancel.

        Raises:
            KeyError: If the transport is not registered.
        """
        transport = self._transports.get(transport_name)
        if transport is None:
            raise KeyError(f"Transport '{transport_name}' not registered.")

        await transport.cancel(request_id)
        self._publish_event("transport.request_cancelled", {
            "transport": transport_name,
            "request_id": request_id,
        })

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def health(self, transport_name: str) -> bool:
        """Check health of a specific transport.

        Args:
            transport_name: Transport identifier.

        Returns:
            True if healthy.
        """
        transport = self._transports.get(transport_name)
        if transport is None:
            return False

        try:
            return await transport.health()
        except Exception:
            return False

    async def health_all(self) -> dict[str, bool]:
        """Check health of all registered transports.

        Returns:
            Dict mapping transport name to health status.
        """
        results: dict[str, bool] = {}
        for name, transport in self._transports.items():
            try:
                results[name] = await transport.health()
            except Exception:
                results[name] = False
        return results

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------

    def select_for_provider(self, provider_id: str, supported_transports: list[str]) -> str | None:
        """Select the best transport for a provider.

        Args:
            provider_id: The provider identifier.
            supported_transports: List of transport names the provider supports.

        Returns:
            Best transport name, or None if no match.
        """
        for t in supported_transports:
            if t in self._transports:
                return t
        return None

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish a transport event.

        Args:
            event_type: The event type string.
            data: Event payload.
        """
        if self._event_bus is None:
            return
        try:
            from workflow_orchestrator.core.event_bus import Event
            self._event_bus.publish(Event(type=event_type, data=data, source="transport_runtime"))
        except Exception:
            pass
