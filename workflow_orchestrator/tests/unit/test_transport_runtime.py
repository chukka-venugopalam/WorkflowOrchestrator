"""Unit tests for Transport Runtime and transport implementations."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from workflow_orchestrator.transports.transport import (
    Transport,
    TransportRequest,
    TransportResponse,
    TransportError,
    TransportStatus,
)


# ---------------------------------------------------------------------------
# Transport Runtime tests
# ---------------------------------------------------------------------------


class TestTransportRuntime:
    """Tests for TransportRuntime."""

    @pytest.fixture
    def transport_runtime(self):
        """Create a transport runtime with mocked transport."""
        from workflow_orchestrator.runtime import TransportRuntime

        runtime = TransportRuntime()
        transport = MagicMock(spec=Transport)
        transport.send = AsyncMock(return_value=TransportResponse(body="ok"))
        transport.send_stream = AsyncMock()
        transport.cancel = AsyncMock()
        transport.health = AsyncMock(return_value=True)
        transport.transport_type = "test_transport"
        runtime.register("test", transport)
        return runtime

    @pytest.mark.asyncio
    async def test_register_and_get(self):
        """Test registering and getting a transport."""
        from workflow_orchestrator.runtime import TransportRuntime

        runtime = TransportRuntime()
        transport = MagicMock(spec=Transport)

        runtime.register("test", transport)
        assert runtime.get("test") is transport

    @pytest.mark.asyncio
    async def test_send(self, transport_runtime):
        """Test sending a request through a transport."""
        request = TransportRequest(url="http://test.com", method="GET")
        response = await transport_runtime.send("test", request)

        assert response is not None
        assert response.body == "ok"

    @pytest.mark.asyncio
    async def test_send_not_found(self, transport_runtime):
        """Test sending through an unregistered transport."""
        request = TransportRequest(url="http://test.com")

        with pytest.raises(KeyError, match="not registered"):
            await transport_runtime.send("nonexistent", request)

    @pytest.mark.asyncio
    async def test_health(self, transport_runtime):
        """Test checking transport health."""
        healthy = await transport_runtime.health("test")
        assert healthy is True

    @pytest.mark.asyncio
    async def test_health_not_found(self, transport_runtime):
        """Test health check for unregistered transport."""
        healthy = await transport_runtime.health("nonexistent")
        assert healthy is False

    @pytest.mark.asyncio
    async def test_health_all(self, transport_runtime):
        """Test health check for all transports."""
        results = await transport_runtime.health_all()
        assert "test" in results
        assert results["test"] is True

    @pytest.mark.asyncio
    async def test_connect(self, transport_runtime):
        """Test connecting a transport."""
        success = await transport_runtime.connect("test")
        assert success is True

    @pytest.mark.asyncio
    async def test_disconnect(self, transport_runtime):
        """Test disconnecting a transport."""
        success = await transport_runtime.disconnect("test")
        assert success is True

    @pytest.mark.asyncio
    async def test_list_transport_types(self, transport_runtime):
        """Test listing transport types."""
        types = transport_runtime.list_transport_types()
        assert "test" in types

    def test_select_for_provider(self, transport_runtime):
        """Test selecting a transport for a provider."""
        name = transport_runtime.select_for_provider("test-provider", ["test"])
        assert name == "test"

        name = transport_runtime.select_for_provider("test-provider", ["nonexistent"])
        assert name is None


# ---------------------------------------------------------------------------
# CLI Command Transport tests
# ---------------------------------------------------------------------------


class TestCliCommandTransport:
    """Tests for CliCommandTransport."""

    @pytest.mark.asyncio
    async def test_send_success(self):
        """Test executing a successful CLI command."""
        from workflow_orchestrator.transports import CliCommandTransport

        transport = CliCommandTransport(shell=True)
        request = TransportRequest(body="echo 'hello'", timeout_seconds=10)

        response = await transport.send(request)
        assert response.success is True
        assert "hello" in response.body

    @pytest.mark.asyncio
    async def test_send_no_command(self):
        """Test sending with no command."""
        from workflow_orchestrator.transports import CliCommandTransport
        from workflow_orchestrator.transports.transport import TransportError

        transport = CliCommandTransport()
        request = TransportRequest()

        with pytest.raises(TransportError):
            await transport.send(request)

    @pytest.mark.asyncio
    async def test_health(self):
        """Test transport health check."""
        from workflow_orchestrator.transports import CliCommandTransport

        transport = CliCommandTransport()
        healthy = await transport.health()
        assert healthy is True

    @pytest.mark.asyncio
    async def test_cancel(self):
        """Test cancelling a command."""
        from workflow_orchestrator.transports import CliCommandTransport

        transport = CliCommandTransport()
        # Should not raise
        await transport.cancel("test-request")


# ---------------------------------------------------------------------------
# Transport base classes tests
# ---------------------------------------------------------------------------


class TestTransportModels:
    """Tests for transport data models."""

    def test_transport_request_defaults(self):
        """Test TransportRequest default values."""
        request = TransportRequest()
        assert request.url == ""
        assert request.method == "GET"
        assert request.timeout_seconds == 30

    def test_transport_request_custom(self):
        """Test TransportRequest with custom values."""
        request = TransportRequest(
            url="http://test.com",
            method="POST",
            body="test body",
            timeout_seconds=60,
        )
        assert request.url == "http://test.com"
        assert request.method == "POST"
        assert request.body == "test body"

    def test_transport_response_defaults(self):
        """Test TransportResponse default values."""
        response = TransportResponse()
        assert response.status_code == 200
        assert response.success is True
        assert response.error == ""

    def test_transport_error_defaults(self):
        """Test TransportError default values."""
        error = TransportError(message="test error")
        assert error.message == "test error"
        assert error.status_code == 500
        assert error.recoverable is False

    def test_transport_status_values(self):
        """Test TransportStatus enum values."""
        assert TransportStatus.PENDING.value == "pending"
        assert TransportStatus.COMPLETED.value == "completed"
        assert TransportStatus.FAILED.value == "failed"
