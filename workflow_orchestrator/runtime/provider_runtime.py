"""Provider Runtime — manages provider lifecycle, selection, and execution.

Coordinates between the Decision Engine, Provider Registry, Context Engine,
Artifact Manager, Event Bus, and Session Manager to execute provider tasks.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Optional

from workflow_orchestrator.intelligence.models import (
    ExecutionRequest,
    ExecutionResult,
    ProviderHealth,
    ProviderStatus,
    RoutingDecision,
)
from workflow_orchestrator.providers.registry.provider_registry_runtime import ProviderRegistryRuntime

logger = logging.getLogger(__name__)


class ProviderRuntime:
    """Runtime orchestrator for provider lifecycle and execution.

    Integrates with:
    - ProviderRegistryRuntime for provider management
    - Decision Engine for provider selection
    - Context Engine for context assembly
    - Artifact Manager for artifact storage
    - Event Bus for event publishing
    - Session Manager for session tracking

    Usage:
        >>> runtime = ProviderRuntime(provider_registry_runtime)
        >>> result = await runtime.execute(provider_id="anthropic.claude", request=exec_request)
    """

    def __init__(
        self,
        provider_registry_runtime: ProviderRegistryRuntime,
        event_bus: Any = None,
        context_engine: Any = None,
        artifact_manager: Any = None,
        session_manager: Any = None,
    ) -> None:
        """Initialize the Provider Runtime.

        Args:
            provider_registry_runtime: The provider registry runtime.
            event_bus: Optional EventBus for publishing events.
            context_engine: Optional ContextEngine for context assembly.
            artifact_manager: Optional ArtifactManager for storing artifacts.
            session_manager: Optional SessionManager for session tracking.
        """
        self._provider_registry_runtime = provider_registry_runtime
        self._event_bus = event_bus
        self._context_engine = context_engine
        self._artifact_manager = artifact_manager
        self._session_manager = session_manager

    @property
    def provider_registry_runtime(self) -> ProviderRegistryRuntime:
        """The underlying provider registry runtime."""
        return self._provider_registry_runtime

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------

    async def initialize_all(self) -> dict[str, bool]:
        """Initialize all registered providers.

        Returns:
            Dict mapping provider ID to initialization success.
        """
        return await self._provider_registry_runtime.initialize_all()

    async def shutdown_all(self) -> None:
        """Shut down all providers gracefully."""
        await self._provider_registry_runtime.shutdown_all()

    async def connect(self, provider_id: str) -> bool:
        """Connect to a specific provider.

        Args:
            provider_id: The provider identifier.

        Returns:
            True if connected successfully.
        """
        success = await self._provider_registry_runtime.connect(provider_id)
        if success:
            self._publish_event("provider.connected", {"provider_id": provider_id})
        else:
            self._publish_event("provider.connection_failed", {"provider_id": provider_id})
        return success

    async def disconnect(self, provider_id: str) -> bool:
        """Disconnect from a specific provider.

        Args:
            provider_id: The provider identifier.

        Returns:
            True if disconnected successfully.
        """
        success = await self._provider_registry_runtime.disconnect(provider_id)
        if success:
            self._publish_event("provider.disconnected", {"provider_id": provider_id})
        return success

    async def health(self, provider_id: str) -> ProviderHealth | None:
        """Check the health of a provider.

        Args:
            provider_id: The provider identifier.

        Returns:
            ProviderHealth status.
        """
        return await self._provider_registry_runtime.check_health(provider_id)

    async def health_all(self) -> dict[str, ProviderHealth]:
        """Check health of all registered providers.

        Returns:
            Dict mapping provider ID to health status.
        """
        return await self._provider_registry_runtime.check_all_health()

    def status(self, provider_id: str) -> ProviderStatus:
        """Get the current status of a provider.

        Args:
            provider_id: The provider identifier.

        Returns:
            Current provider status.
        """
        return self._provider_registry_runtime.status(provider_id)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(
        self,
        provider_id: str,
        request: ExecutionRequest,
        routing_decision: RoutingDecision | None = None,
        session_id: str | None = None,
    ) -> ExecutionResult:
        """Execute a task through a provider.

        Full execution flow:
        1. Resolve provider
        2. Assemble context (if context engine available)
        3. Execute through provider
        4. Store artifacts (if artifact manager available)
        5. Record in session (if session manager available)
        6. Publish events

        Args:
            provider_id: The provider to use.
            request: The execution request.
            routing_decision: Optional routing decision context.
            session_id: Optional session ID for tracking.

        Returns:
            ExecutionResult with output and artifacts.
        """
        # Resolve provider
        provider = self._provider_registry_runtime.registry.lookup(provider_id)
        if provider is None:
            self._publish_event("provider.not_found", {"provider_id": provider_id})
            return ExecutionResult(
                task_id=request.task_id,
                success=False,
                error_message=f"Provider '{provider_id}' not found",
            )

        # Ensure initialized
        try:
            await provider.initialize()
        except Exception as exc:
            return ExecutionResult(
                task_id=request.task_id,
                success=False,
                error_message=f"Failed to initialize provider '{provider_id}': {exc}",
            )

        # Track in session
        if session_id and self._session_manager:
            self._session_manager.record_task(
                session_id=session_id,
                task_id=request.task_id or uuid.uuid4().hex[:12],
                capability_id=request.capability.id if request.capability else "",
                provider_id=provider_id,
                agent_id=routing_decision.selected_agent_id if routing_decision else "",
                goal=request.goal,
            )

        # Publish pre-execution event
        self._publish_event("provider.selected", {
            "provider_id": provider_id,
            "task_id": request.task_id,
            "capability": request.capability.id if request.capability else "",
            "routing_confidence": routing_decision.confidence if routing_decision else 0.0,
        })

        # Execute
        start_time = time.time()
        try:
            result = await provider.submit(request)
            result.duration_ms = (time.time() - start_time) * 1000

            # Store artifact if successful and artifact manager available
            if result.success and self._artifact_manager:
                artifact_ref = self._artifact_manager.store(
                    content=result.output.encode("utf-8"),
                    source=f"provider:{provider_id}",
                    workflow_run_id=session_id or "",
                    step_name=request.capability.id if request.capability else "general",
                    content_type="text/plain",
                    tags=["provider_output", provider_id],
                    metadata={
                        "task_id": request.task_id,
                        "provider_id": provider_id,
                        "capability": request.capability.id if request.capability else "",
                        "duration_ms": result.duration_ms,
                    },
                )
                result.metadata["artifact_id"] = artifact_ref.artifact_id

            # Update session
            if session_id and self._session_manager:
                self._session_manager.update_task(
                    session_id=session_id,
                    task_id=request.task_id,
                    status="completed" if result.success else "failed",
                    result=result,
                )

            # Publish result event
            if result.success:
                self._publish_event("provider.completed", {
                    "provider_id": provider_id,
                    "task_id": request.task_id,
                    "duration_ms": result.duration_ms,
                })
            else:
                self._publish_event("provider.failed", {
                    "provider_id": provider_id,
                    "task_id": request.task_id,
                    "error": result.error_message,
                })

            return result
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            self._publish_event("provider.failed", {
                "provider_id": provider_id,
                "task_id": request.task_id,
                "error": str(exc),
            })
            return ExecutionResult(
                task_id=request.task_id,
                success=False,
                error_message=str(exc),
                duration_ms=duration_ms,
            )

    async def cancel(self, provider_id: str, task_id: str) -> None:
        """Cancel an in-flight provider task.

        Args:
            provider_id: The provider identifier.
            task_id: The task identifier to cancel.
        """
        provider = self._provider_registry_runtime.registry.lookup(provider_id)
        if provider:
            await provider.cancel(task_id)
            self._publish_event("provider.cancelled", {
                "provider_id": provider_id,
                "task_id": task_id,
            })

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_metrics(self, provider_id: str) -> dict[str, Any] | None:
        """Get metrics for a provider.

        Args:
            provider_id: The provider identifier.

        Returns:
            Provider metrics dict.
        """
        return self._provider_registry_runtime.get_metrics(provider_id)

    def get_all_metrics(self) -> dict[str, dict[str, Any]]:
        """Get metrics for all providers.

        Returns:
            Dict mapping provider ID to metrics.
        """
        return self._provider_registry_runtime.get_all_metrics()

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish a provider event.

        Args:
            event_type: The event type string.
            data: Event payload.
        """
        if self._event_bus is None:
            return
        try:
            from workflow_orchestrator.core.event_bus import Event
            self._event_bus.publish(Event(type=event_type, data=data, source="provider_runtime"))
        except Exception:
            pass
