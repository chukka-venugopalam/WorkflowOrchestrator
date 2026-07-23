"""Agent Runtime — manages agent lifecycle, selection, and task execution.

Coordinates between the Decision Engine, Agent Registry, Context Engine,
Artifact Manager, Event Bus, and Session Manager to execute agent tasks.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Optional

from workflow_orchestrator.intelligence.agent import IAgent
from workflow_orchestrator.intelligence.agent_registry import AgentRegistry
from workflow_orchestrator.intelligence.models import (
    AgentStatus,
    ExecutionRequest,
    ExecutionResult,
    RoutingDecision,
)

logger = logging.getLogger(__name__)


class AgentRuntime:
    """Runtime orchestrator for agent lifecycle and task execution.

    Integrates with:
    - AgentRegistry for agent management
    - Decision Engine for agent selection
    - Context Engine for context assembly
    - Artifact Manager for artifact storage
    - Event Bus for event publishing
    - Session Manager for session tracking

    Usage:
        >>> runtime = AgentRuntime(agent_registry)
        >>> result = await runtime.execute(agent_id="claude-code", request=exec_request)
    """

    def __init__(
        self,
        agent_registry: AgentRegistry,
        event_bus: Any = None,
        context_engine: Any = None,
        artifact_manager: Any = None,
        session_manager: Any = None,
    ) -> None:
        """Initialize the Agent Runtime.

        Args:
            agent_registry: The agent registry.
            event_bus: Optional EventBus for publishing events.
            context_engine: Optional ContextEngine for context assembly.
            artifact_manager: Optional ArtifactManager for storing artifacts.
            session_manager: Optional SessionManager for session tracking.
        """
        self._agent_registry = agent_registry
        self._event_bus = event_bus
        self._context_engine = context_engine
        self._artifact_manager = artifact_manager
        self._session_manager = session_manager
        self._launched_agents: set[str] = set()

    @property
    def agent_registry(self) -> AgentRegistry:
        """The underlying agent registry."""
        return self._agent_registry

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------

    async def launch(self, agent_id: str) -> bool:
        """Launch a specific agent.

        Args:
            agent_id: The agent identifier.

        Returns:
            True if launched successfully.
        """
        agent = self._agent_registry.lookup(agent_id)
        if agent is None:
            logger.error("Agent '%s' not found", agent_id)
            return False

        try:
            await agent.launch()
            self._launched_agents.add(agent_id)
            self._publish_event("agent.started", {"agent_id": agent_id})
            return True
        except Exception as exc:
            logger.error("Failed to launch agent '%s': %s", agent_id, exc)
            self._publish_event("agent.launch_failed", {"agent_id": agent_id, "error": str(exc)})
            return False

    async def launch_all(self) -> dict[str, bool]:
        """Launch all registered agents.

        Returns:
            Dict mapping agent ID to launch success.
        """
        results: dict[str, bool] = {}
        for agent_id in self._agent_registry.list_ids():
            results[agent_id] = await self.launch(agent_id)
        return results

    async def shutdown(self, agent_id: str) -> bool:
        """Shut down a specific agent.

        Args:
            agent_id: The agent identifier.

        Returns:
            True if shut down successfully.
        """
        agent = self._agent_registry.lookup(agent_id)
        if agent is None:
            return False

        try:
            await agent.shutdown()
            self._launched_agents.discard(agent_id)
            self._publish_event("agent.shutdown", {"agent_id": agent_id})
            return True
        except Exception as exc:
            logger.warning("Error shutting down agent '%s': %s", agent_id, exc)
            return False

    async def shutdown_all(self) -> None:
        """Shut down all launched agents."""
        for agent_id in list(self._launched_agents):
            await self.shutdown(agent_id)

    async def heartbeat(self, agent_id: str, task_id: str = "") -> AgentStatus:
        """Check if an agent is alive and responsive.

        Args:
            agent_id: The agent identifier.
            task_id: Optional task identifier.

        Returns:
            Current AgentStatus.
        """
        agent = self._agent_registry.lookup(agent_id)
        if agent is None:
            return AgentStatus.FAILED
        try:
            return await agent.heartbeat(task_id or "_status_")
        except Exception:
            return AgentStatus.FAILED

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(
        self,
        agent_id: str,
        request: ExecutionRequest,
        routing_decision: RoutingDecision | None = None,
        session_id: str | None = None,
    ) -> ExecutionResult:
        """Execute a task through an agent.

        Full execution flow:
        1. Resolve agent
        2. Ensure agent is launched
        3. Execute through agent
        4. Store artifacts (if artifact manager available)
        5. Record in session (if session manager available)
        6. Publish events

        Args:
            agent_id: The agent to use.
            request: The execution request.
            routing_decision: Optional routing decision context.
            session_id: Optional session ID for tracking.

        Returns:
            ExecutionResult with output and artifacts.
        """
        # Resolve agent
        agent = self._agent_registry.lookup(agent_id)
        if agent is None:
            self._publish_event("agent.not_found", {"agent_id": agent_id})
            return ExecutionResult(
                task_id=request.task_id,
                success=False,
                error_message=f"Agent '{agent_id}' not found",
            )

        # Ensure agent is launched
        try:
            if agent_id not in self._launched_agents:
                await self.launch(agent_id)
        except Exception as exc:
            return ExecutionResult(
                task_id=request.task_id,
                success=False,
                error_message=f"Failed to launch agent '{agent_id}': {exc}",
            )

        # Track in session
        if session_id and self._session_manager:
            self._session_manager.record_task(
                session_id=session_id,
                task_id=request.task_id or uuid.uuid4().hex[:12],
                capability_id=request.capability.id if request.capability else "",
                provider_id=routing_decision.selected_provider_id if routing_decision else "",
                agent_id=agent_id,
                goal=request.goal,
            )

        # Publish pre-execution event
        self._publish_event("agent.task_started", {
            "agent_id": agent_id,
            "task_id": request.task_id,
            "goal": request.goal[:100],
        })

        # Execute
        start_time = time.time()
        try:
            result = await agent.execute(request)
            result.duration_ms = (time.time() - start_time) * 1000

            # Store artifacts if successful and artifact manager available
            if result.success and self._artifact_manager:
                artifact_ref = self._artifact_manager.store(
                    content=result.output.encode("utf-8"),
                    source=f"agent:{agent_id}",
                    workflow_run_id=session_id or "",
                    step_name=request.capability.id if request.capability else "general",
                    content_type="text/plain",
                    tags=["agent_output", agent_id],
                    metadata={
                        "task_id": request.task_id,
                        "agent_id": agent_id,
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
                self._publish_event("agent.finished", {
                    "agent_id": agent_id,
                    "task_id": request.task_id,
                    "duration_ms": result.duration_ms,
                })
            else:
                self._publish_event("agent.task_failed", {
                    "agent_id": agent_id,
                    "task_id": request.task_id,
                    "error": result.error_message,
                })

            return result
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            self._publish_event("agent.task_failed", {
                "agent_id": agent_id,
                "task_id": request.task_id,
                "error": str(exc),
            })
            return ExecutionResult(
                task_id=request.task_id,
                success=False,
                error_message=str(exc),
                duration_ms=duration_ms,
            )

    async def cancel(self, agent_id: str, task_id: str) -> None:
        """Cancel a running task on an agent.

        Args:
            agent_id: The agent identifier.
            task_id: The task identifier to cancel.
        """
        agent = self._agent_registry.lookup(agent_id)
        if agent:
            await agent.cancel(task_id)
            self._publish_event("agent.task_cancelled", {
                "agent_id": agent_id,
                "task_id": task_id,
            })

    async def resume(self, agent_id: str, task_id: str) -> ExecutionResult:
        """Resume a paused or interrupted task on an agent.

        Args:
            agent_id: The agent identifier.
            task_id: The task identifier to resume.

        Returns:
            ExecutionResult with resumed execution status.
        """
        agent = self._agent_registry.lookup(agent_id)
        if agent is None:
            return ExecutionResult(
                task_id=task_id,
                success=False,
                error_message=f"Agent '{agent_id}' not found",
            )
        return await agent.resume(task_id)

    def status(self, agent_id: str) -> AgentStatus:
        """Get the current status of an agent.

        Args:
            agent_id: The agent identifier.

        Returns:
            Current AgentStatus.
        """
        return AgentStatus.RUNNING if agent_id in self._launched_agents else AgentStatus.IDLE

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an agent event.

        Args:
            event_type: The event type string.
            data: Event payload.
        """
        if self._event_bus is None:
            return
        try:
            from workflow_orchestrator.core.event_bus import Event
            self._event_bus.publish(Event(type=event_type, data=data, source="agent_runtime"))
        except Exception:
            pass
