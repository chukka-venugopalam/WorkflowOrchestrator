"""Base provider — common implementation for all provider adapters.

Provides shared lifecycle tracking, health management, metrics collection,
and event publishing. All concrete providers should subclass this.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, AsyncIterator, Optional

from workflow_orchestrator.intelligence.models import (
    Capability,
    CostEstimate,
    ExecutionErrorType,
    ExecutionRequest,
    ExecutionResult,
    ProviderHealth,
    ProviderManifest,
    ProviderStatus,
)
from workflow_orchestrator.intelligence.provider import IProvider
from workflow_orchestrator.providers.base.provider_metrics import ProviderMetrics

logger = logging.getLogger(__name__)


class BaseProvider(IProvider):
    """Base provider adapter with common functionality.

    Subclasses must implement:
    - ``manifest()`` — return the provider's metadata
    - ``_execute_impl()`` — actual execution logic
    - ``_stream_impl()`` — streaming execution (optional)

    Subclasses may override:
    - ``_initialize_impl()`` — custom initialization
    - ``_shutdown_impl()`` — custom shutdown
    - ``_health_impl()`` — custom health check
    - ``_cancel_impl()`` — custom cancellation
    - ``_estimate_cost_impl()`` — custom cost estimation
    """

    def __init__(self) -> None:
        self._status: ProviderStatus = ProviderStatus.UNINITIALIZED
        self._initialized: bool = False
        self._shutdown_requested: bool = False
        self._active_tasks: dict[str, asyncio.Task[Any]] = {}
        self._initialized_at: float = 0.0
        self._metrics: ProviderMetrics = ProviderMetrics(provider_id=self.provider_id)
        self._event_bus: Any = None

    # ------------------------------------------------------------------
    # Public lifecycle (final — subclasses override _impl methods)
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Initialize the provider. Calls ``_initialize_impl()``."""
        if self._initialized:
            return
        self._status = ProviderStatus.INITIALIZING
        try:
            await self._initialize_impl()
            self._initialized = True
            self._status = ProviderStatus.AVAILABLE
            self._initialized_at = time.time()
            logger.info("Provider '%s' initialized", self.provider_id)
            self._publish_event("provider.initialized", {"provider_id": self.provider_id})
        except Exception as exc:
            self._status = ProviderStatus.UNAVAILABLE
            logger.error("Failed to initialize provider '%s': %s", self.provider_id, exc)
            self._publish_event("provider.initialization_failed", {
                "provider_id": self.provider_id,
                "error": str(exc),
            })
            raise

    async def shutdown(self) -> None:
        """Shut down the provider. Calls ``_shutdown_impl()``."""
        if self._shutdown_requested:
            return
        self._shutdown_requested = True
        self._status = ProviderStatus.SHUTDOWN

        # Cancel all active tasks
        for task_id, task in list(self._active_tasks.items()):
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        self._active_tasks.clear()

        try:
            await self._shutdown_impl()
            logger.info("Provider '%s' shut down", self.provider_id)
            self._publish_event("provider.shutdown", {"provider_id": self.provider_id})
        except Exception as exc:
            logger.warning("Error during provider '%s' shutdown: %s", self.provider_id, exc)

    async def health(self) -> ProviderHealth:
        """Check provider health. Calls ``_health_impl()``."""
        try:
            return await self._health_impl()
        except Exception as exc:
            logger.warning("Health check failed for '%s': %s", self.provider_id, exc)
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.UNAVAILABLE,
                message=str(exc),
            )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Alias for submit() for provider execution."""
        return await self.submit(request)

    async def submit(self, request: ExecutionRequest) -> ExecutionResult:
        """Submit a task for execution and wait for completion.

        Args:
            request: The execution request.

        Returns:
            ExecutionResult with output and artifacts.
        """
        self._ensure_initialized()

        if not request.task_id:
            request.task_id = uuid.uuid4().hex[:12]

        start_time = time.time()
        try:
            logger.debug("Provider '%s' submitting task '%s'", self.provider_id, request.task_id)
            result = await self._execute_impl(request)
            duration_ms = (time.time() - start_time) * 1000
            result.duration_ms = duration_ms
            result.task_id = request.task_id

            if result.success:
                self._metrics.record_success(
                    latency_ms=duration_ms,
                    tokens_input=result.token_usage.get("input", 0),
                    tokens_output=result.token_usage.get("output", 0),
                    cost=result.cost.estimated_cost if result.cost else 0.0,
                )
                self._publish_event("provider.completed", {
                    "provider_id": self.provider_id,
                    "task_id": request.task_id,
                    "duration_ms": duration_ms,
                })
            else:
                error_type = result.error_type.value if result.error_type else "unknown"
                self._metrics.record_failure(latency_ms=duration_ms, error_type=error_type)
                self._publish_event("provider.failed", {
                    "provider_id": self.provider_id,
                    "task_id": request.task_id,
                    "error": result.error_message,
                    "error_type": error_type,
                })

            return result
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            self._metrics.record_failure(latency_ms=duration_ms, error_type="internal_error")
            self._publish_event("provider.failed", {
                "provider_id": self.provider_id,
                "task_id": request.task_id,
                "error": str(exc),
                "error_type": "internal_error",
            })
            return ExecutionResult(
                task_id=request.task_id,
                success=False,
                error_type=ExecutionErrorType.INTERNAL_ERROR,
                error_message=str(exc),
                duration_ms=duration_ms,
            )

    async def stream(self, request: ExecutionRequest) -> AsyncIterator[ExecutionResult]:
        """Submit a task and stream partial results.

        Args:
            request: The execution request.

        Yields:
            Partial ExecutionResult objects.
        """
        self._ensure_initialized()

        if not request.task_id:
            request.task_id = uuid.uuid4().hex[:12]

        start_time = time.time()
        try:
            async for partial in self._stream_impl(request):
                partial.duration_ms = (time.time() - start_time) * 1000
                partial.task_id = request.task_id
                yield partial
                if partial.success:
                    self._metrics.record_success(
                        latency_ms=(time.time() - start_time) * 1000,
                        tokens_input=partial.token_usage.get("input", 0),
                        tokens_output=partial.token_usage.get("output", 0),
                    )
                    self._publish_event("provider.completed", {
                        "provider_id": self.provider_id,
                        "task_id": request.task_id,
                    })
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            self._metrics.record_failure(latency_ms=duration_ms, error_type="stream_error")
            yield ExecutionResult(
                task_id=request.task_id,
                success=False,
                error_type=ExecutionErrorType.INTERNAL_ERROR,
                error_message=str(exc),
                duration_ms=duration_ms,
            )

    async def cancel(self, task_id: str) -> None:
        """Cancel an in-flight task.

        Args:
            task_id: The task identifier to cancel.

        Raises:
            ValueError: If the task is not found.
        """
        task = self._active_tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
            self._active_tasks.pop(task_id, None)
            logger.debug("Cancelled task '%s' on provider '%s'", task_id, self.provider_id)

        await self._cancel_impl(task_id)
        self._publish_event("provider.cancelled", {
            "provider_id": self.provider_id,
            "task_id": task_id,
        })

    async def status(self, task_id: str) -> ExecutionResult:
        """Check the status of a submitted task.

        Args:
            task_id: The task identifier.

        Returns:
            ExecutionResult with current status.
        """
        task = self._active_tasks.get(task_id)
        if task is None:
            return ExecutionResult(
                task_id=task_id,
                success=False,
                error_type=ExecutionErrorType.UNKNOWN,
                error_message=f"Task '{task_id}' not found",
            )
        if task.done():
            try:
                return task.result()
            except Exception as exc:
                return ExecutionResult(
                    task_id=task_id,
                    success=False,
                    error_type=ExecutionErrorType.INTERNAL_ERROR,
                    error_message=str(exc),
                )
        return ExecutionResult(
            task_id=task_id,
            success=False,
            status=ProviderStatus.AVAILABLE,
            output="Task is still running",
        )

    # ------------------------------------------------------------------
    # Estimation
    # ------------------------------------------------------------------

    async def estimate_cost(self, request: ExecutionRequest) -> CostEstimate:
        """Estimate the cost of executing a request.

        Args:
            request: The execution request.

        Returns:
            CostEstimate with estimated cost.
        """
        return await self._estimate_cost_impl(request)

    async def estimate_latency(self, request: ExecutionRequest) -> float:
        """Estimate the latency in milliseconds.

        Args:
            request: The execution request.

        Returns:
            Estimated latency in milliseconds.
        """
        return self._metrics.average_latency_ms or 1000.0

    # ------------------------------------------------------------------
    # Subclass hooks (override in implementations)
    # ------------------------------------------------------------------

    async def _initialize_impl(self) -> None:
        """Subclass hook: custom initialization logic."""
        pass

    async def _shutdown_impl(self) -> None:
        """Subclass hook: custom shutdown logic."""
        pass

    async def _health_impl(self) -> ProviderHealth:
        """Subclass hook: custom health check.

        Returns:
            Default health status.
        """
        return ProviderHealth(
            provider_id=self.provider_id,
            status=self._status,
            latency_ms=self._metrics.average_latency_ms,
            error_rate=self._metrics.error_rate,
            last_checked=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
        )

    async def _cancel_impl(self, task_id: str) -> None:
        """Subclass hook: custom cancellation logic."""
        pass

    async def _execute_impl(self, request: ExecutionRequest) -> ExecutionResult:
        """Subclass hook: actual execution logic.

        Must be implemented by subclasses.

        Args:
            request: The execution request.

        Returns:
            ExecutionResult with task output.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError(f"Provider '{self.provider_id}' must implement _execute_impl")

    async def _stream_impl(self, request: ExecutionRequest) -> AsyncIterator[ExecutionResult]:
        """Subclass hook: streaming execution.

        Defaults to non-streaming fallback by calling ``_execute_impl()``
        and yielding the full result as a single chunk.

        Args:
            request: The execution request.

        Yields:
            ExecutionResult objects as they become available.
        """
        result = await self._execute_impl(request)
        yield result

    async def capabilities(self) -> list[Capability]:
        """Get the list of capabilities this provider offers.

        Default implementation returns capabilities from the manifest.

        Returns:
            List of Capability objects.
        """
        return list(self.manifest().capabilities)

    async def _estimate_cost_impl(self, request: ExecutionRequest) -> CostEstimate:
        """Subclass hook: custom cost estimation.

        Args:
            request: The execution request.

        Returns:
            Default cost estimate (zero).
        """
        return CostEstimate(
            provider_id=self.provider_id,
            estimated_cost=0.0,
            confidence=0.0,
        )

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def set_event_bus(self, event_bus: Any) -> None:
        """Set the event bus for publishing provider events.

        Args:
            event_bus: Event bus instance.
        """
        self._event_bus = event_bus

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish a provider event if an event bus is available.

        Args:
            event_type: The event type string.
            data: Event payload.
        """
        if self._event_bus is None:
            return
        try:
            from workflow_orchestrator.core.event_bus import Event
            self._event_bus.publish(Event(type=event_type, data=data, source=f"provider:{self.provider_id}"))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_initialized(self) -> None:
        """Ensure the provider is initialized before execution.

        Raises:
            RuntimeError: If the provider is not initialized.
        """
        if not self._initialized:
            raise RuntimeError(f"Provider '{self.provider_id}' is not initialized. Call initialize() first.")
        if self._shutdown_requested:
            raise RuntimeError(f"Provider '{self.provider_id}' has been shut down.")

    @property
    def metrics(self) -> ProviderMetrics:
        """Get the provider's execution metrics."""
        return self._metrics

    @property
    def status(self) -> ProviderStatus:
        """Get the current provider status."""
        return self._status

    def supports_streaming(self) -> bool:
        """Whether this provider supports streaming.

        Returns:
            True if ``_stream_impl`` is overridden.
        """
        return type(self)._stream_impl is not BaseProvider._stream_impl
