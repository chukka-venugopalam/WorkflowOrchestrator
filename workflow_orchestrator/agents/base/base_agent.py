"""Base agent — common implementation for all coding agent adapters.

Provides shared lifecycle tracking, workspace management, task tracking,
and event publishing. All concrete agents should subclass this.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.intelligence.agent import IAgent
from workflow_orchestrator.intelligence.models import (
    AgentManifest,
    AgentStatus,
    Capability,
    ExecutionErrorType,
    ExecutionRequest,
    ExecutionResult,
)

logger = logging.getLogger(__name__)


class BaseAgent(IAgent):
    """Base agent adapter with common functionality.

    Subclasses must implement:
    - ``manifest()`` — return the agent's metadata
    - ``_execute_impl()`` — actual execution logic

    Subclasses may override:
    - ``_launch_impl()`` — custom launch logic
    - ``_shutdown_impl()`` — custom shutdown logic
    - ``_cancel_impl()`` — custom cancellation logic
    - ``_resume_impl()`` — custom resume logic
    """

    def __init__(self, workspace_base: Path | str | None = None) -> None:
        """Initialize the base agent.

        Args:
            workspace_base: Base directory for agent workspaces.
        """
        self._status: AgentStatus = AgentStatus.IDLE
        self._launched: bool = False
        self._shutdown_requested: bool = False
        self._active_tasks: dict[str, asyncio.Task[Any]] = {}
        self._workspace_base = Path(workspace_base) if workspace_base else Path.cwd() / ".agent_workspaces"
        self._current_workspace: Path | None = None
        self._event_bus: Any = None

    # ------------------------------------------------------------------
    # Public lifecycle (final — subclasses override _impl methods)
    # ------------------------------------------------------------------

    async def launch(self) -> None:
        """Launch the agent. Calls ``_launch_impl()``."""
        if self._launched:
            return
        self._status = AgentStatus.LAUNCHING
        try:
            await self._launch_impl()
            self._launched = True
            self._status = AgentStatus.IDLE
            logger.info("Agent '%s' launched", self.agent_id)
            self._publish_event("agent.launched", {"agent_id": self.agent_id})
        except Exception as exc:
            self._status = AgentStatus.FAILED
            logger.error("Failed to launch agent '%s': %s", self.agent_id, exc)
            self._publish_event("agent.launch_failed", {
                "agent_id": self.agent_id,
                "error": str(exc),
            })
            raise

    async def shutdown(self) -> None:
        """Shut down the agent gracefully. Calls ``_shutdown_impl()``."""
        if self._shutdown_requested:
            return
        self._shutdown_requested = True

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
            self._status = AgentStatus.COMPLETED
            logger.info("Agent '%s' shut down", self.agent_id)
            self._publish_event("agent.shutdown", {"agent_id": self.agent_id})
        except Exception as exc:
            logger.warning("Error during agent '%s' shutdown: %s", self.agent_id, exc)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute a task with this agent.

        Args:
            request: The execution request with goal and context.

        Returns:
            ExecutionResult with agent output.
        """
        self._ensure_launched()
        if not request.task_id:
            request.task_id = uuid.uuid4().hex[:12]

        self._status = AgentStatus.RUNNING
        start_time = time.time()

        try:
            self._publish_event("agent.task_started", {
                "agent_id": self.agent_id,
                "task_id": request.task_id,
                "goal": request.goal[:100],
            })

            result = await self._execute_impl(request)
            result.task_id = request.task_id
            result.duration_ms = (time.time() - start_time) * 1000

            self._status = AgentStatus.IDLE
            if result.success:
                self._publish_event("agent.task_completed", {
                    "agent_id": self.agent_id,
                    "task_id": request.task_id,
                    "duration_ms": result.duration_ms,
                })
            else:
                self._publish_event("agent.task_failed", {
                    "agent_id": self.agent_id,
                    "task_id": request.task_id,
                    "error": result.error_message,
                })

            return result
        except Exception as exc:
            self._status = AgentStatus.FAILED
            duration_ms = (time.time() - start_time) * 1000
            self._publish_event("agent.task_failed", {
                "agent_id": self.agent_id,
                "task_id": request.task_id,
                "error": str(exc),
            })
            return ExecutionResult(
                task_id=request.task_id,
                success=False,
                error_type=ExecutionErrorType.INTERNAL_ERROR,
                error_message=str(exc),
                duration_ms=duration_ms,
            )

    async def cancel(self, task_id: str) -> None:
        """Cancel a running task.

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

        await self._cancel_impl(task_id)
        self._status = AgentStatus.IDLE
        self._publish_event("agent.task_cancelled", {
            "agent_id": self.agent_id,
            "task_id": task_id,
        })

    async def resume(self, task_id: str) -> ExecutionResult:
        """Resume a previously paused or interrupted task.

        Args:
            task_id: The task identifier to resume.

        Returns:
            ExecutionResult with resumed execution status.
        """
        self._ensure_launched()
        self._status = AgentStatus.RUNNING
        try:
            result = await self._resume_impl(task_id)
            result.task_id = task_id
            self._status = AgentStatus.IDLE
            return result
        except Exception as exc:
            self._status = AgentStatus.FAILED
            return ExecutionResult(
                task_id=task_id,
                success=False,
                error_type=ExecutionErrorType.INTERNAL_ERROR,
                error_message=str(exc),
            )

    async def status(self, task_id: str) -> ExecutionResult:
        """Check the status of a running or completed task.

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
                status=self._status,
                error_message=f"Task '{task_id}' not found in active tasks",
            )
        if task.done():
            try:
                return task.result()
            except Exception as exc:
                return ExecutionResult(
                    task_id=task_id,
                    success=False,
                    status=AgentStatus.FAILED,
                    error_message=str(exc),
                )
        return ExecutionResult(
            task_id=task_id,
            success=False,
            status=AgentStatus.RUNNING,
            output="Task is still running",
        )

    async def heartbeat(self, task_id: str) -> AgentStatus:
        """Check if the agent is still alive and responsive.

        Args:
            task_id: The task identifier to check.

        Returns:
            Current AgentStatus.
        """
        return self._status

    async def supported_capabilities(self) -> list[Capability]:
        """Get the list of capabilities this agent supports.

        Returns:
            List of Capability objects.
        """
        return list(self.manifest().capabilities)

    # ------------------------------------------------------------------
    # Subclass hooks
    # ------------------------------------------------------------------

    async def _launch_impl(self) -> None:
        """Subclass hook: custom launch logic."""
        pass

    async def _shutdown_impl(self) -> None:
        """Subclass hook: custom shutdown logic."""
        pass

    async def _cancel_impl(self, task_id: str) -> None:
        """Subclass hook: custom cancellation logic."""
        pass

    async def _resume_impl(self, task_id: str) -> ExecutionResult:
        """Subclass hook: custom resume logic.

        Args:
            task_id: The task identifier to resume.

        Returns:
            ExecutionResult.
        """
        return ExecutionResult(
            task_id=task_id,
            success=False,
            error_message="Resume not implemented for this agent",
        )

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
        raise NotImplementedError(f"Agent '{self.agent_id}' must implement _execute_impl")

    # ------------------------------------------------------------------
    # Workspace management
    # ------------------------------------------------------------------

    def create_workspace(self, workspace_id: str | None = None) -> Path:
        """Create a workspace directory for agent execution.

        Args:
            workspace_id: Optional workspace identifier.

        Returns:
            Path to the created workspace.
        """
        ws_id = workspace_id or uuid.uuid4().hex[:12]
        workspace = self._workspace_base / ws_id
        workspace.mkdir(parents=True, exist_ok=True)
        self._current_workspace = workspace
        logger.debug("Created workspace at %s", workspace)
        return workspace

    def get_workspace(self) -> Path | None:
        """Get the current workspace path.

        Returns:
            Current workspace path, or None.
        """
        return self._current_workspace

    def cleanup_workspace(self) -> None:
        """Clean up the current workspace."""
        if self._current_workspace and self._current_workspace.exists():
            import shutil
            shutil.rmtree(self._current_workspace, ignore_errors=True)
            self._current_workspace = None

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def set_event_bus(self, event_bus: Any) -> None:
        """Set the event bus for publishing agent events.

        Args:
            event_bus: Event bus instance.
        """
        self._event_bus = event_bus

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an agent event if an event bus is available.

        Args:
            event_type: The event type string.
            data: Event payload.
        """
        if self._event_bus is None:
            return
        try:
            from workflow_orchestrator.core.event_bus import Event
            self._event_bus.publish(Event(type=event_type, data=data, source=f"agent:{self.agent_id}"))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_launched(self) -> None:
        """Ensure the agent is launched before execution.

        Raises:
            RuntimeError: If the agent is not launched.
        """
        if not self._launched:
            raise RuntimeError(f"Agent '{self.agent_id}' is not launched. Call launch() first.")
        if self._shutdown_requested:
            raise RuntimeError(f"Agent '{self.agent_id}' has been shut down.")
