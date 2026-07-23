"""Session Runtime — persistent session management with pause/resume/restore.

Manages the full lifecycle of sessions including persistence to disk,
state transitions, artifact tracking, and execution graph storage.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.intelligence.models import (
    ArtifactReference,
    ExecutionResult,
    Session,
    SessionState,
    TaskRecord,
)
from workflow_orchestrator.intelligence.session import SessionManager

logger = logging.getLogger(__name__)


class SessionRuntime:
    """Runtime for persistent session management.

    Extends the SessionManager with disk persistence, project-bound
    sessions, pause/resume/restore capabilities, and execution
    graph tracking.

    Usage:
        >>> runtime = SessionRuntime(session_manager, project_dir=Path("./my-project"))
        >>> session = await runtime.create_session(project="my-app", workflow="build")
        >>> await runtime.save()
        >>> restored = await runtime.restore(session.session_id)
    """

    def __init__(
        self,
        session_manager: SessionManager,
        project_dir: Path | str | None = None,
        event_bus: Any = None,
        config: Any = None,
    ) -> None:
        """Initialize the Session Runtime.

        Args:
            session_manager: The session manager for in-memory tracking.
            project_dir: Project directory for persistence.
            event_bus: Optional EventBus for publishing events.
            config: Optional configuration manager.
        """
        self._session_manager = session_manager
        self._project_dir = Path(project_dir) if project_dir else Path.cwd()
        self._state_dir = self._project_dir / ".state"
        self._event_bus = event_bus
        self._config = config
        self._session_file = self._state_dir / "session.json"

    @property
    def session_manager(self) -> SessionManager:
        """The underlying session manager."""
        return self._session_manager

    @property
    def state_dir(self) -> Path:
        """The .state directory path."""
        return self._state_dir

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
        """Create a new session with persistence.

        Args:
            project: Project name or identifier.
            workflow: Workflow name or identifier.
            session_id: Optional explicit session ID.
            metadata: Additional session metadata.

        Returns:
            The newly created Session.
        """
        session = self._session_manager.create_session(
            project=project,
            workflow=workflow,
            session_id=session_id,
            metadata=metadata,
        )
        self._ensure_state_dir()
        self._save_session_file(session)
        self._publish_event("session.created", {
            "session_id": session.session_id,
            "project": project,
            "workflow": workflow,
        })
        return session

    def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID.

        Args:
            session_id: The session identifier.

        Returns:
            The Session, or None if not found.
        """
        return self._session_manager.get_session(session_id)

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
        return self._session_manager.list_sessions(state=state, project=project)

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def pause_session(self, session_id: str) -> Session | None:
        """Pause an active session.

        Args:
            session_id: The session identifier.

        Returns:
            The updated Session, or None if not found.
        """
        session = self._session_manager.pause_session(session_id)
        if session:
            self._save_session_file(session)
            self._publish_event("session.paused", {"session_id": session_id})
        return session

    def resume_session(self, session_id: str) -> Session | None:
        """Resume a paused session.

        Args:
            session_id: The session identifier.

        Returns:
            The updated Session, or None if not found.
        """
        session = self._session_manager.resume_session(session_id)
        if session:
            self._save_session_file(session)
            self._publish_event("session.restored", {"session_id": session_id})
        return session

    def complete_session(self, session_id: str, success: bool = True) -> Session | None:
        """Mark a session as completed or failed.

        Args:
            session_id: The session identifier.
            success: True for completed, False for failed.

        Returns:
            The updated Session, or None if not found.
        """
        session = self._session_manager.complete_session(session_id, success=success)
        if session:
            self._save_session_file(session)
            self._publish_event("session.completed", {
                "session_id": session_id,
                "state": session.state.value,
            })
        return session

    def cancel_session(self, session_id: str) -> Session | None:
        """Cancel a session.

        Args:
            session_id: The session identifier.

        Returns:
            The updated Session, or None if not found.
        """
        session = self._session_manager.cancel_session(session_id)
        if session:
            self._save_session_file(session)
            self._publish_event("session.cancelled", {"session_id": session_id})
        return session

    # ------------------------------------------------------------------
    # Provider/Agent assignment
    # ------------------------------------------------------------------

    def set_provider(self, session_id: str, provider_id: str) -> bool:
        """Set the active provider for a session.

        Args:
            session_id: The session identifier.
            provider_id: The provider identifier.

        Returns:
            True if successful.
        """
        result = self._session_manager.set_provider(session_id, provider_id)
        if result:
            self._save_providers_file(session_id)
        return result

    def set_agent(self, session_id: str, agent_id: str) -> bool:
        """Set the active agent for a session.

        Args:
            session_id: The session identifier.
            agent_id: The agent identifier.

        Returns:
            True if successful.
        """
        result = self._session_manager.set_agent(session_id, agent_id)
        if result:
            self._save_agents_file(session_id)
        return result

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
            capability_id: The capability used.
            provider_id: The provider that executed this task.
            agent_id: The agent that executed this task.
            goal: The task goal.

        Returns:
            The TaskRecord, or None if session not found.
        """
        task = self._session_manager.record_task(
            session_id=session_id,
            task_id=task_id,
            capability_id=capability_id,
            provider_id=provider_id,
            agent_id=agent_id,
            goal=goal,
        )
        if task:
            self._save_timeline_file(session_id)
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
            The updated TaskRecord, or None if not found.
        """
        return self._session_manager.update_task(
            session_id=session_id,
            task_id=task_id,
            status=status,
            result=result,
            artifacts=artifacts,
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Save all session data to disk."""
        self._ensure_state_dir()
        for session in self._session_manager.list_sessions():
            self._save_session_file(session)

    def restore(self, session_id: str) -> Session | None:
        """Restore a session from disk.

        Args:
            session_id: The session identifier.

        Returns:
            The restored Session, or None if not found.
        """
        session_file = self._state_dir / "session.json"
        if not session_file.exists():
            return None

        try:
            data = json.loads(session_file.read_text(encoding="utf-8"))
            if data.get("session_id") != session_id:
                return None

            session = self._session_manager.create_session(
                project=data.get("project", ""),
                workflow=data.get("workflow", ""),
                session_id=session_id,
                metadata=data.get("metadata", {}),
            )
            session.state = SessionState(data.get("state", "active"))

            # Restore provider and agent
            provider_id = data.get("provider_id", "")
            agent_id = data.get("agent_id", "")
            if provider_id:
                session.provider_id = provider_id
            if agent_id:
                session.agent_id = agent_id

            self._publish_event("session.restored", {"session_id": session_id})
            return session
        except Exception as exc:
            logger.warning("Failed to restore session '%s': %s", session_id, exc)
            return None

    def restore_latest(self) -> Session | None:
        """Restore the latest session from disk.

        Returns:
            The most recent Session, or None if none found.
        """
        session_file = self._state_dir / "session.json"
        if not session_file.exists():
            return None
        try:
            data = json.loads(session_file.read_text(encoding="utf-8"))
            return self.restore(data.get("session_id", ""))
        except Exception:
            return None

    # ------------------------------------------------------------------
    # File management
    # ------------------------------------------------------------------

    def _ensure_state_dir(self) -> Path:
        """Ensure the .state directory exists.

        Returns:
            The state directory path.
        """
        self._state_dir.mkdir(parents=True, exist_ok=True)
        (self._state_dir / "artifacts").mkdir(exist_ok=True)
        (self._state_dir / "history").mkdir(exist_ok=True)
        (self._state_dir / "summaries").mkdir(exist_ok=True)
        (self._state_dir / "contract").mkdir(exist_ok=True)
        (self._state_dir / "context").mkdir(exist_ok=True)
        return self._state_dir

    def _save_session_file(self, session: Session) -> None:
        """Save session data to the session.json file.

        Args:
            session: The session to save.
        """
        try:
            data = {
                "session_id": session.session_id,
                "project": session.project,
                "workflow": session.workflow,
                "provider_id": session.provider_id,
                "agent_id": session.agent_id,
                "state": session.state.value,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "completed_at": session.completed_at,
                "metadata": session.metadata,
            }
            self._session_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to save session file: %s", exc)

    def _save_providers_file(self, session_id: str) -> None:
        """Save provider configuration to disk.

        Args:
            session_id: The session identifier.
        """
        session = self._session_manager.get_session(session_id)
        if session is None:
            return
        try:
            providers_file = self._state_dir / "providers.json"
            data = {"active_provider": session.provider_id, "session_id": session_id}
            providers_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to save providers file: %s", exc)

    def _save_agents_file(self, session_id: str) -> None:
        """Save agent configuration to disk.

        Args:
            session_id: The session identifier.
        """
        session = self._session_manager.get_session(session_id)
        if session is None:
            return
        try:
            agents_file = self._state_dir / "agents.json"
            data = {"active_agent": session.agent_id, "session_id": session_id}
            agents_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to save agents file: %s", exc)

    def _save_timeline_file(self, session_id: str) -> None:
        """Save task timeline to disk.

        Args:
            session_id: The session identifier.
        """
        tasks = self._session_manager.get_task_history(session_id)
        try:
            timeline_file = self._state_dir / "timeline.json"
            timeline_data = [
                {
                    "task_id": t.task_id,
                    "capability_id": t.capability_id,
                    "provider_id": t.provider_id,
                    "agent_id": t.agent_id,
                    "goal": t.goal[:100] if t.goal else "",
                    "status": t.status,
                    "started_at": t.started_at,
                    "completed_at": t.completed_at,
                }
                for t in tasks
            ]
            timeline_file.write_text(json.dumps(timeline_data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to save timeline file: %s", exc)

    # ------------------------------------------------------------------
    # Contract version tracking
    # ------------------------------------------------------------------

    def save_contract_version(self, session_id: str, contract_version: str) -> None:
        """Save the contract version for a session.

        Args:
            session_id: The session identifier.
            contract_version: The contract version string.
        """
        try:
            contract_file = self._state_dir / "contract" / "version.json"
            contract_file.write_text(
                json.dumps({"session_id": session_id, "version": contract_version, "updated_at": datetime.now(timezone.utc).isoformat()}, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Failed to save contract version: %s", exc)

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish a session event.

        Args:
            event_type: The event type string.
            data: Event payload.
        """
        if self._event_bus is None:
            return
        try:
            from workflow_orchestrator.core.event_bus import Event
            self._event_bus.publish(Event(type=event_type, data=data, source="session_runtime"))
        except Exception:
            pass
