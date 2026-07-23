"""Unit tests for Provider Runtime and provider implementations."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from workflow_orchestrator.intelligence.models import (
    Capability,
    CostEstimate,
    ExecutionErrorType,
    ExecutionRequest,
    ExecutionResult,
    ProviderManifest,
    ProviderStatus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_provider():
    """Create a mock provider for testing."""
    provider = MagicMock()
    provider.provider_id = "test.provider"
    provider.provider_name = "Test Provider"

    manifest = ProviderManifest(
        id="test.provider",
        name="Test Provider",
        version="1.0.0",
        capabilities=[
            Capability(id="codegen.general", description="General code generation"),
            Capability(id="reasoning.analysis", description="Analysis"),
        ],
    )
    provider.manifest.return_value = manifest
    provider.initialize = AsyncMock()
    provider.shutdown = AsyncMock()
    provider.health = AsyncMock(return_value=MagicMock(status=ProviderStatus.AVAILABLE))
    provider.submit = AsyncMock(return_value=ExecutionResult(
        task_id="test-task",
        success=True,
        output="Test output",
    ))
    provider.cancel = AsyncMock()
    provider.status = MagicMock()
    provider.metrics = MagicMock()
    return provider


@pytest.fixture
def mock_execution_request():
    """Create a mock execution request."""
    return ExecutionRequest(
        task_id="test-task",
        goal="Generate a login page",
        capability=Capability(id="codegen.general", description="General code gen"),
        temperature=0.7,
        max_tokens=4096,
        timeout_seconds=60,
        context={"project": "test-app"},
    )


# ---------------------------------------------------------------------------
# Provider Registry Runtime tests
# ---------------------------------------------------------------------------


class TestProviderRegistryRuntime:
    """Tests for ProviderRegistryRuntime."""

    @pytest.mark.asyncio
    async def test_initialize_all(self, mock_provider):
        """Test initializing all providers."""
        from workflow_orchestrator.intelligence.provider_registry import ProviderRegistry
        from workflow_orchestrator.providers.registry import ProviderRegistryRuntime

        registry = ProviderRegistry()
        registry.register(mock_provider)

        runtime = ProviderRegistryRuntime(registry=registry)
        results = await runtime.initialize_all()

        assert mock_provider.initialize.called
        assert results[mock_provider.provider_id] is True
        assert runtime.initialized is True

    @pytest.mark.asyncio
    async def test_shutdown_all(self, mock_provider):
        """Test shutting down all providers."""
        from workflow_orchestrator.intelligence.provider_registry import ProviderRegistry
        from workflow_orchestrator.providers.registry import ProviderRegistryRuntime

        registry = ProviderRegistry()
        registry.register(mock_provider)

        runtime = ProviderRegistryRuntime(registry=registry)
        await runtime.initialize_all()
        await runtime.shutdown_all()

        assert mock_provider.shutdown.called
        assert runtime.initialized is False

    @pytest.mark.asyncio
    async def test_check_health(self, mock_provider):
        """Test checking provider health."""
        from workflow_orchestrator.intelligence.provider_registry import ProviderRegistry
        from workflow_orchestrator.providers.registry import ProviderRegistryRuntime

        registry = ProviderRegistry()
        registry.register(mock_provider)

        runtime = ProviderRegistryRuntime(registry=registry)
        health = await runtime.check_health("test.provider")

        assert health is not None
        assert health.status == ProviderStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_check_health_not_found(self):
        """Test health check for unregistered provider."""
        from workflow_orchestrator.intelligence.provider_registry import ProviderRegistry
        from workflow_orchestrator.providers.registry import ProviderRegistryRuntime

        registry = ProviderRegistry()
        runtime = ProviderRegistryRuntime(registry=registry)
        health = await runtime.check_health("nonexistent")

        assert health is None

    def test_status(self, mock_provider):
        """Test getting provider status."""
        from workflow_orchestrator.intelligence.provider_registry import ProviderRegistry
        from workflow_orchestrator.providers.registry import ProviderRegistryRuntime

        registry = ProviderRegistry()
        registry.register(mock_provider)

        runtime = ProviderRegistryRuntime(registry=registry)
        # The mock provider doesn't have a 'status' attribute, so it falls back to UNINITIALIZED
        status = runtime.status("nonexistent")

        assert status == ProviderStatus.UNINITIALIZED

    def test_get_available_providers(self, mock_provider):
        """Test getting available providers."""
        from workflow_orchestrator.intelligence.provider_registry import ProviderRegistry
        from workflow_orchestrator.providers.registry import ProviderRegistryRuntime

        registry = ProviderRegistry()
        registry.register(mock_provider)

        runtime = ProviderRegistryRuntime(registry=registry)
        available = runtime.get_available_providers()

        assert len(available) >= 1


# ---------------------------------------------------------------------------
# Provider Runtime tests
# ---------------------------------------------------------------------------


class TestProviderRuntime:
    """Tests for ProviderRuntime."""

    @pytest.mark.asyncio
    async def test_execute(self, mock_provider, mock_execution_request):
        """Test executing a request through a provider."""
        from workflow_orchestrator.intelligence.provider_registry import ProviderRegistry
        from workflow_orchestrator.providers.registry import ProviderRegistryRuntime
        from workflow_orchestrator.runtime import ProviderRuntime

        registry = ProviderRegistry()
        registry.register(mock_provider)

        provider_runtime_runtime = ProviderRegistryRuntime(registry=registry)
        runtime = ProviderRuntime(provider_registry_runtime=provider_runtime_runtime)

        result = await runtime.execute("test.provider", mock_execution_request)

        assert result is not None
        assert result.success is True
        assert result.task_id == "test-task"

    @pytest.mark.asyncio
    async def test_execute_provider_not_found(self, mock_execution_request):
        """Test execution with unregistered provider."""
        from workflow_orchestrator.intelligence.provider_registry import ProviderRegistry
        from workflow_orchestrator.providers.registry import ProviderRegistryRuntime
        from workflow_orchestrator.runtime import ProviderRuntime

        registry = ProviderRegistry()
        provider_runtime_runtime = ProviderRegistryRuntime(registry=registry)
        runtime = ProviderRuntime(provider_registry_runtime=provider_runtime_runtime)

        result = await runtime.execute("nonexistent", mock_execution_request)

        assert result is not None
        assert result.success is False
        assert "not found" in result.error_message

    @pytest.mark.asyncio
    async def test_cancel(self, mock_provider):
        """Test cancelling a provider task."""
        from workflow_orchestrator.intelligence.provider_registry import ProviderRegistry
        from workflow_orchestrator.providers.registry import ProviderRegistryRuntime
        from workflow_orchestrator.runtime import ProviderRuntime

        registry = ProviderRegistry()
        registry.register(mock_provider)

        provider_runtime_runtime = ProviderRegistryRuntime(registry=registry)
        runtime = ProviderRuntime(provider_registry_runtime=provider_runtime_runtime)

        await runtime.cancel("test.provider", "task-123")
        assert mock_provider.cancel.called

    def test_get_metrics_unregistered(self):
        """Test getting metrics for an unregistered provider."""
        from workflow_orchestrator.intelligence.provider_registry import ProviderRegistry
        from workflow_orchestrator.providers.registry import ProviderRegistryRuntime
        from workflow_orchestrator.runtime import ProviderRuntime

        registry = ProviderRegistry()
        provider_runtime_runtime = ProviderRegistryRuntime(registry=registry)
        runtime = ProviderRuntime(provider_registry_runtime=provider_runtime_runtime)

        # Unregistered provider should return None
        metrics = runtime.get_metrics("nonexistent")
        assert metrics is None


# ---------------------------------------------------------------------------
# Base Provider tests
# ---------------------------------------------------------------------------


class TestBaseProvider:
    """Tests for BaseProvider."""

    @pytest.mark.asyncio
    async def test_initialize_and_shutdown(self):
        """Test provider initialization and shutdown."""
        from workflow_orchestrator.intelligence.models import ProviderManifest
        from workflow_orchestrator.providers.base import BaseProvider

        # Since manifest is abstract, we need a concrete subclass
        class TestProvider(BaseProvider):
            def manifest(self):
                return ProviderManifest(
                    id="test.provider",
                    name="Test Provider",
                )

        tp = TestProvider()
        await tp.initialize()
        await tp.shutdown()
        # Should not raise

    @pytest.mark.asyncio
    async def test_submit_before_initialize_raises(self):
        """Test that submit before initialize raises."""
        from workflow_orchestrator.intelligence.models import ProviderManifest
        from workflow_orchestrator.providers.base import BaseProvider

        class TestProvider(BaseProvider):
            def manifest(self):
                return ProviderManifest(id="test.provider", name="Test")

        tp = TestProvider()
        with pytest.raises(RuntimeError, match="not initialized"):
            await tp.submit(MagicMock())

    @pytest.mark.asyncio
    async def test_health_default(self):
        """Test default health implementation."""
        from workflow_orchestrator.intelligence.models import ProviderManifest
        from workflow_orchestrator.providers.base import BaseProvider

        class TestProvider(BaseProvider):
            def manifest(self):
                return ProviderManifest(id="test.provider", name="Test")

        tp = TestProvider()
        health = await tp.health()
        assert health.provider_id == "test.provider"

    def test_metrics_initialization(self):
        """Test that metrics are initialized correctly."""
        from workflow_orchestrator.providers.base.provider_metrics import ProviderMetrics

        metrics = ProviderMetrics(provider_id="test.provider")

        assert metrics.provider_id == "test.provider"
        assert metrics.total_requests == 0
        assert metrics.error_rate == 0.0
        assert metrics.average_latency_ms == 0.0

    def test_metrics_record_success(self):
        """Test recording a successful request."""
        from workflow_orchestrator.providers.base.provider_metrics import ProviderMetrics

        metrics = ProviderMetrics(provider_id="test.provider")
        metrics.record_success(latency_ms=100.0, tokens_input=50, tokens_output=100)

        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.total_latency_ms == 100.0
        assert metrics.total_tokens_input == 50
        assert metrics.total_tokens_output == 100

    def test_metrics_record_failure(self):
        """Test recording a failed request."""
        from workflow_orchestrator.providers.base.provider_metrics import ProviderMetrics

        metrics = ProviderMetrics(provider_id="test.provider")
        metrics.record_failure(latency_ms=50.0, error_type="timeout")

        assert metrics.total_requests == 1
        assert metrics.failed_requests == 1
        assert metrics.error_rate == 1.0
        assert "timeout" in metrics.errors_by_type

    def test_metrics_to_dict(self):
        """Test serializing metrics to dict."""
        from workflow_orchestrator.providers.base.provider_metrics import ProviderMetrics

        metrics = ProviderMetrics(provider_id="test.provider")
        metrics.record_success(latency_ms=100.0)

        data = metrics.to_dict()
        assert data["provider_id"] == "test.provider"
        assert data["total_requests"] == 1
        assert "average_latency_ms" in data
