"""Session manager for tracking units of work across providers and agents.

Tracks project, provider, agent, artifacts, workflow, task history,
execution history, timestamps, and state for each session.

Supports pausing, resuming, and completing sessions with full
audit trail of all activity.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from workflow_orchestrator.intelligence.models import (
    ArtifactReference,
    ExecutionResult,
    Session,
    SessionState,
    TaskRecord,
)

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages sessions for tracking work across providers and agents.

    A session represents a unit of work (e.g., a workflow execution)
    and tracks all activity within it: which provider and agent were
    used, what tasks were executed, what artifacts were produced,
    and the overall state.

    Usage:
        >>> mgr = SessionManager()
        >>> session = mgr.create_session(project="my-app", workflow="build")
        >>> mgr.set_provider(session.session_id, "anthropic.claude")
        >>> mgr.set_agent(session.session_id, "claude-code")
        >>> task = mgr.record_task(session.session_id, task_id="t1", capability_id="codegen.nextjs")
        >>> mgr.complete_session(session.session_id)
    """

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_session(
        self,
        project: str = "",
        workflow: str = "",
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Session:
        """Create a new session.

        Args:
            project: Project name or identifier.
            workflow: Workflow name or identifier.
            session_id: Optional explicit session ID.
            metadata: Additional session metadata.

        Returns:
            The newly created Session.
        """
        sid = session_id or uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat()

        session = Session(
            session_id=sid,
            project=project,
            workflow=workflow,
            created_at=now,
            updated_at=now,
            state=SessionState.ACTIVE,
            metadata=metadata or {},
        )

        self._sessions[sid] = session
        logger.info("Created session '%s' (project: %s, workflow: %s)", sid, project, workflow)
        return session

    def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID.

        Args:
            session_id: The session identifier.

        Returns:
            The Session, or None if not found.
        """
        return self._sessions.get(session_id)

    def get_session_required(self, session_id: str) -> Session:
        """Get a session by ID, raising if not found.

        Args:
            session_id: The session identifier.

        Returns:
            The Session.

        Raises:
            KeyError: If the session is not found.
        """
        session = self.get_session(session_id)
        if session is None:
            raise KeyError(f"Session '{session_id}' not found.")
        return session

    def list_sessions(
        self,
        state: SessionState | None = None,
        project: str | None = None,
    ) -> list[Session]:
        """List sessions, optionally filtered.

        Args:
            state: Optional filter by session state.
            project: Optional filter by project name.

        Returns:
            List of matching sessions.
        """
        results = list(self._sessions.values())

        if state is not None:
            results = [s for s in results if s.state == state]

        if project is not None:
            results = [s for s in results if s.project == project]

        return sorted(results, key=lambda s: s.created_at, reverse=True)

    # ------------------------------------------------------------------
    # Session state
    # ------------------------------------------------------------------

    def pause_session(self, session_id: str) -> Session | None:
        """Pause an active session.

        Args:
            session_id: The session identifier.

        Returns:
            The updated Session, or None if not found.
        """
        session = self.get_session(session_id)
        if session is None:
            return None

        session.state = SessionState.PAUSED
        session.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info("Paused session '%s'", session_id)
        return session

    def resume_session(self, session_id: str) -> Session | None:
        """Resume a paused session.

        Args:
            session_id: The session identifier.

        Returns:
            The updated Session, or None if not found.
        """
        session = self.get_session(session_id)
        if session is None:
            return None

        session.state = SessionState.ACTIVE
        session.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info("Resumed session '%s'", session_id)
        return session

    def complete_session(
        self,
        session_id: str,
        success: bool = True,
    ) -> Session | None:
        """Mark a session as completed or failed.

        Args:
            session_id: The session identifier.
            success: True for completed, False for failed.

        Returns:
            The updated Session, or None if not found.
        """
        session = self.get_session(session_id)
        if session is None:
            return None

        now = datetime.now(timezone.utc).isoformat()
        session.state = SessionState.COMPLETED if success else SessionState.FAILED
        session.completed_at = now
        session.updated_at = now
        logger.info("Completed session '%s' with state %s", session_id, session.state.value)
        return session

    def cancel_session(self, session_id: str) -> Session | None:
        """Cancel a session.

        Args:
            session_id: The session identifier.

        Returns:
            The updated Session, or None if not found.
        """
        session = self.get_session(session_id)
        if session is None:
            return None

        now = datetime.now(timezone.utc).isoformat()
        session.state = SessionState.CANCELLED
        session.completed_at = now
        session.updated_at = now
        logger.info("Cancelled session '%s'", session_id)
        return session

    # ------------------------------------------------------------------
    # Provider / Agent assignment
    # ------------------------------------------------------------------

    def set_provider(self, session_id: str, provider_id: str) -> bool:
        """Set the active provider for a session.

        Args:
            session_id: The session identifier.
            provider_id: The provider identifier.

        Returns:
            True if successful.
        """
        session = self.get_session(session_id)
        if session is None:
            return False
        session.provider_id = provider_id
        session.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def set_agent(self, session_id: str, agent_id: str) -> bool:
        """Set the active agent for a session.

        Args:
            session_id: The session identifier.
            agent_id: The agent identifier.

        Returns:
            True if successful.
        """
        session = self.get_session(session_id)
        if session is None:
            return False
        session.agent_id = agent_id
        session.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def get_active_provider(self, session_id: str) -> str | None:
        """Get the currently active provider for a session.

        Args:
            session_id: The session identifier.

        Returns:
            Provider ID, or None if not found or not set.
        """
        session = self.get_session(session_id)
        if session is None:
            return None
        return session.provider_id or None

    def get_active_agent(self, session_id: str) -> str | None:
        """Get the currently active agent for a session.

        Args:
            session_id: The session identifier.

        Returns:
            Agent ID, or None if not found or not set.
        """
        session = self.get_session(session_id)
        if session is None:
            return None
        return session.agent_id or None

    # ------------------------------------------------------------------
    # Task tracking
    # ------------------------------------------------------------------

    def record_task(
        self,
        session_id: str,
        task_id: str,
        capability_id: str = "",
        provider_id: str = "",
        agent_id: str = "",
        goal: str = "",
    ) -> TaskRecord | None:
        """Record a task in a session's history.

        Args:
            session_id: The session identifier.
            task_id: Unique task identifier.
            capability_id: The capability used for this task.
            provider_id: The provider that executed this task.
            agent_id: The agent that executed this task.
            goal: The task goal.

        Returns:
            The TaskRecord, or None if session not found.
        """
        session = self.get_session(session_id)
        if session is None:
            return None

        now = datetime.now(timezone.utc).isoformat()
        task = TaskRecord(
            task_id=task_id,
            capability_id=capability_id or session.metadata.get("capability_id", ""),
            provider_id=provider_id or session.provider_id,
            agent_id=agent_id or session.agent_id,
            goal=goal,
            status="pending",
            started_at=now,
        )
        session.task_history.append(task)
        session.updated_at = now
        return task

    def update_task(
        self,
        session_id: str,
        task_id: str,
        status: str | None = None,
        result: ExecutionResult | None = None,
        artifacts: list[ArtifactReference] | None = None,
    ) -> TaskRecord | None:
        """Update a task's status and result.

        Args:
            session_id: The session identifier.
            task_id: The task identifier.
            status: New status string.
            result: Execution result.
            artifacts: Artifacts produced.

        Returns:
            The updated TaskRecord, or None if session/task not found.
        """
        session = self.get_session(session_id)
        if session is None:
            return None

        for task in session.task_history:
            if task.task_id == task_id:
                if status is not None:
                    task.status = status
                if result is not None:
                    task.result = result
                    task.duration_ms = result.duration_ms
                    if result.success:
                        task.completed_at = datetime.now(timezone.utc).isoformat()
                if artifacts is not None:
                    task.artifacts.extend(artifacts)
                    # Also add to session-level artifacts
                    session.artifacts.extend(artifacts)
                session.updated_at = datetime.now(timezone.utc).isoformat()
                return task

        return None

    def get_task(self, session_id: str, task_id: str) -> TaskRecord | None:
        """Get a task record from a session.

        Args:
            session_id: The session identifier.
            task_id: The task identifier.

        Returns:
            The TaskRecord, or None if not found.
        """
        session = self.get_session(session_id)
        if session is None:
            return None
        for task in session.task_history:
            if task.task_id == task_id:
                return task
        return None

    def get_task_history(self, session_id: str) -> list[TaskRecord]:
        """Get the full task history for a session.

        Args:
            session_id: The session identifier.

        Returns:
            List of TaskRecord objects, most recent first.
        """
        session = self.get_session(session_id)
        if session is None:
            return []
        return list(reversed(session.task_history))

    # ------------------------------------------------------------------
    # Artifact tracking
    # ------------------------------------------------------------------

    def add_artifact(
        self,
        session_id: str,
        artifact: ArtifactReference,
    ) -> bool:
        """Add an artifact to a session.

        Args:
            session_id: The session identifier.
            artifact: The artifact to add.

        Returns:
            True if successful.
        """
        session = self.get_session(session_id)
        if session is None:
            return False
        session.artifacts.append(artifact)
        session.updated_at = datetime.now(timezone.utc).isoformat()
        return True

    def get_artifacts(self, session_id: str) -> list[ArtifactReference]:
        """Get all artifacts for a session.

        Args:
            session_id: The session identifier.

        Returns:
            List of ArtifactReference objects.
        """
        session = self.get_session(session_id)
        if session is None:
            return []
        return list(session.artifacts)

    # ------------------------------------------------------------------
    # Count
    # ------------------------------------------------------------------

    @property
    def count(self) -> int:
        """Number of active sessions."""
        return len(self._sessions)

    def count_by_state(self) -> dict[str, int]:
        """Count sessions by state.

        Returns:
            Dict mapping state value to count.
        """
        counts: dict[str, int] = {}
        for session in self._sessions.values():
            state = session.state.value
            counts[state] = counts.get(state, 0) + 1
        return counts
