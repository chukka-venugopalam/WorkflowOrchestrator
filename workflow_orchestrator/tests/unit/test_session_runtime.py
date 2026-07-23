"""Unit tests for Session Runtime and project memory."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from workflow_orchestrator.intelligence.models import Session, SessionState


class TestSessionRuntime:
    """Tests for Session Runtime."""

    @pytest.fixture
    def session_runtime(self, tmp_path):
        """Create a session runtime with temp directory."""
        from workflow_orchestrator.intelligence.session import SessionManager
        from workflow_orchestrator.runtime import SessionRuntime

        session_manager = SessionManager()
        return SessionRuntime(
            session_manager=session_manager,
            project_dir=str(tmp_path),
        )

    def test_create_session(self, session_runtime):
        """Test creating a session."""
        session = session_runtime.create_session(project="test-project", workflow="test-workflow")

        assert session.project == "test-project"
        assert session.workflow == "test-workflow"
        assert session.state == SessionState.ACTIVE
        assert session.session_id is not None

    def test_get_session(self, session_runtime):
        """Test getting a session by ID."""
        created = session_runtime.create_session(project="test")
        retrieved = session_runtime.get_session(created.session_id)

        assert retrieved is not None
        assert retrieved.session_id == created.session_id

    def test_pause_and_resume(self, session_runtime):
        """Test pausing and resuming a session."""
        session = session_runtime.create_session(project="test")

        paused = session_runtime.pause_session(session.session_id)
        assert paused is not None
        assert paused.state == SessionState.PAUSED

        resumed = session_runtime.resume_session(session.session_id)
        assert resumed is not None
        assert resumed.state == SessionState.ACTIVE

    def test_complete_session(self, session_runtime):
        """Test completing a session."""
        session = session_runtime.create_session(project="test")

        completed = session_runtime.complete_session(session.session_id)
        assert completed is not None
        assert completed.state == SessionState.COMPLETED

    def test_cancel_session(self, session_runtime):
        """Test cancelling a session."""
        session = session_runtime.create_session(project="test")

        cancelled = session_runtime.cancel_session(session.session_id)
        assert cancelled is not None
        assert cancelled.state == SessionState.CANCELLED

    def test_set_provider(self, session_runtime):
        """Test setting the active provider."""
        session = session_runtime.create_session(project="test")

        result = session_runtime.set_provider(session.session_id, "anthropic.claude")
        assert result is True

        updated = session_runtime.get_session(session.session_id)
        assert updated is not None
        assert updated.provider_id == "anthropic.claude"

    def test_set_agent(self, session_runtime):
        """Test setting the active agent."""
        session = session_runtime.create_session(project="test")

        result = session_runtime.set_agent(session.session_id, "claude-code")
        assert result is True

        updated = session_runtime.get_session(session.session_id)
        assert updated is not None
        assert updated.agent_id == "claude-code"

    def test_record_task(self, session_runtime):
        """Test recording a task."""
        session = session_runtime.create_session(project="test")

        task = session_runtime.record_task(
            session_id=session.session_id,
            task_id="task-1",
            capability_id="codegen.general",
            provider_id="test-provider",
            agent_id="test-agent",
            goal="Do something",
        )

        assert task is not None
        assert task.task_id == "task-1"
        assert task.status == "pending"

    def test_save_and_restore(self, session_runtime):
        """Test saving and restoring a session."""
        session = session_runtime.create_session(project="test", workflow="test-workflow")
        session_runtime.set_provider(session.session_id, "anthropic.claude")
        session_runtime.save()

        restored = session_runtime.restore(session.session_id)
        assert restored is not None
        assert restored.session_id == session.session_id
        assert restored.project == "test"

    def test_state_dir_creation(self, session_runtime):
        """Test that the .state directory is created."""
        session_runtime.create_session(project="test")

        state_dir = session_runtime.state_dir
        assert state_dir.exists()
        assert (state_dir / "artifacts").exists()
        assert (state_dir / "history").exists()
        assert (state_dir / "summaries").exists()
        assert (state_dir / "contract").exists()
        assert (state_dir / "context").exists()


class TestSessionManager:
    """Tests for SessionManager."""

    @pytest.fixture
    def session_manager(self):
        """Create a session manager."""
        from workflow_orchestrator.intelligence.session import SessionManager
        return SessionManager()

    def test_create_and_get(self, session_manager):
        """Test creating and getting a session."""
        session = session_manager.create_session(project="test")
        assert session_manager.get_session(session.session_id) is session

    def test_list_sessions(self, session_manager):
        """Test listing sessions."""
        session_manager.create_session(project="test")
        sessions = session_manager.list_sessions()
        assert len(sessions) >= 1

    def test_list_by_state(self, session_manager):
        """Test listing sessions filtered by state."""
        s1 = session_manager.create_session(project="test")
        session_manager.complete_session(s1.session_id)

        sessions = session_manager.list_sessions(state=SessionState.COMPLETED)
        assert len(sessions) >= 1

    def test_get_task_history(self, session_manager):
        """Test getting task history."""
        session = session_manager.create_session(project="test")
        session_manager.record_task(session.session_id, task_id="t1", capability_id="codegen")
        session_manager.record_task(session.session_id, task_id="t2", capability_id="reasoning")

        history = session_manager.get_task_history(session.session_id)
        assert len(history) == 2

    def test_count_by_state(self, session_manager):
        """Test counting sessions by state."""
        session_manager.create_session(project="test")
        counts = session_manager.count_by_state()
        assert "active" in counts
