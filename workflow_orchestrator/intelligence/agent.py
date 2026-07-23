"""Abstract agent interface for coding agent adapters.

All coding agents (Claude Code, Cursor, Codex, GitHub Copilot,
OpenCode, FreeBuff, etc.) must implement this interface.

Agents are black boxes — only artifacts and results flow back.
The orchestrator manages their lifecycle, workspace isolation,
and capability declarations, but never inspects their internals.

No agent-specific implementations exist in this module.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from workflow_orchestrator.intelligence.models import (
    AgentManifest,
    AgentStatus,
    Capability,
    ExecutionRequest,
    ExecutionResult,
)


class IAgent(ABC):
    """Abstract interface that all coding agents must implement.

    Responsibilities:
    - Declare capabilities via ``manifest()`` and ``supported_capabilities()``
    - Execute tasks via ``execute()``
    - Manage lifecycle via ``launch()``, ``cancel()``, ``resume()``
    - Report status via ``status()``
    - Send heartbeats via ``heartbeat()``

    Usage:
        >>> class ClaudeCodeAgent(IAgent):
        ...     def manifest(self) -> AgentManifest: ...
        ...     async def execute(self, request: ExecutionRequest) -> ExecutionResult: ...
    """

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    async def launch(self) -> None:
        """Launch the agent.

        Called to prepare the agent for task execution. This may
        involve starting a subprocess, establishing a connection,
        or verifying the agent is available on the system.

        Raises:
            RuntimeError: If the agent cannot be launched.
        """
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Shut down the agent gracefully.

        Called to stop the agent and release resources. Any
        in-flight tasks should be cancelled.
        """
        ...

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    @abstractmethod
    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute a task with this agent.

        The agent receives a scoped workspace with explicit file/tool
        permissions. Outputs are normalized into an ExecutionResult
        with diffs, logs, and artifact references.

        Args:
            request: The execution request with goal, context, etc.

        Returns:
            ExecutionResult with output, artifacts, and status.
        """
        ...

    @abstractmethod
    async def cancel(self, task_id: str) -> None:
        """Cancel a running task.

        Args:
            task_id: The task identifier to cancel.

        Raises:
            ValueError: If the task is not found.
        """
        ...

    @abstractmethod
    async def resume(self, task_id: str) -> ExecutionResult:
        """Resume a previously paused or interrupted task.

        Args:
            task_id: The task identifier to resume.

        Returns:
            ExecutionResult with resumed execution status.
        """
        ...

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    @abstractmethod
    async def status(self, task_id: str) -> ExecutionResult:
        """Check the status of a running or completed task.

        Args:
            task_id: The task identifier.

        Returns:
            ExecutionResult with current execution status.
        """
        ...

    @abstractmethod
    async def heartbeat(self, task_id: str) -> AgentStatus:
        """Check if the agent is still alive and responsive.

        Args:
            task_id: The task identifier to check.

        Returns:
            Current AgentStatus of the agent.
        """
        ...

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @abstractmethod
    def manifest(self) -> AgentManifest:
        """Get the agent's declared manifest.

        Returns:
            AgentManifest with metadata, capabilities, and requirements.

        This method must be deterministic and cheap to call.
        """
        ...

    @abstractmethod
    async def supported_capabilities(self) -> list[Capability]:
        """Get the list of capabilities this agent supports.

        Returns:
            List of Capability objects this agent can fulfill.
        """
        ...

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def agent_id(self) -> str:
        """Shortcut to ``self.manifest().id``."""
        return self.manifest().id

    @property
    def agent_name(self) -> str:
        """Shortcut to ``self.manifest().name``."""
        return self.manifest().name
