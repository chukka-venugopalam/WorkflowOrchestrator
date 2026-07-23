"""Unit tests for the SessionManager."""

from __future__ import annotations

from workflow_orchestrator.intelligence.session import SessionManager
from workflow_orchestrator.intelligence.models import (
    ArtifactReference,
    ExecutionResult,
    SessionState,
)


class TestSessionManager:
    def setup_method(self) -> None:
        self.manager = SessionManager()

    def test_create_session(self) -> None:
        session = self.manager.create_session(project="my-app", workflow="build")
        assert session.project == "my-app"
        assert session.workflow == "build"
        assert session.state == SessionState.ACTIVE
        assert session.created_at != ""

    def test_create_session_with_id(self) -> None:
        session = self.manager.create_session(session_id="custom-id")
        assert session.session_id == "custom-id"

    def test_get_session(self) -> None:
        session = self.manager.create_session()
        retrieved = self.manager.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    def test_get_session_not_found(self) -> None:
        assert self.manager.get_session("nonexistent") is None

    def test_get_session_required(self) -> None:
        session = self.manager.create_session()
        assert self.manager.get_session_required(session.session_id) is session

    def test_get_session_required_not_found(self) -> None:
        import pytest
        with pytest.raises(KeyError):
            self.manager.get_session_required("nonexistent")

    def test_pause_and_resume_session(self) -> None:
        session = self.manager.create_session()
        self.manager.pause_session(session.session_id)
        assert self.manager.get_session(session.session_id).state == SessionState.PAUSED

        self.manager.resume_session(session.session_id)
        assert self.manager.get_session(session.session_id).state == SessionState.ACTIVE

    def test_complete_session(self) -> None:
        session = self.manager.create_session()
        self.manager.complete_session(session.session_id, success=True)
        assert self.manager.get_session(session.session_id).state == SessionState.COMPLETED

    def test_fail_session(self) -> None:
        session = self.manager.create_session()
        self.manager.complete_session(session.session_id, success=False)
        assert self.manager.get_session(session.session_id).state == SessionState.FAILED

    def test_cancel_session(self) -> None:
        session = self.manager.create_session()
        self.manager.cancel_session(session.session_id)
        assert self.manager.get_session(session.session_id).state == SessionState.CANCELLED

    def test_set_provider(self) -> None:
        session = self.manager.create_session()
        assert self.manager.set_provider(session.session_id, "anthropic.claude")
        assert self.manager.get_active_provider(session.session_id) == "anthropic.claude"

    def test_set_agent(self) -> None:
        session = self.manager.create_session()
        assert self.manager.set_agent(session.session_id, "claude-code")
        assert self.manager.get_active_agent(session.session_id) == "claude-code"

    def test_set_provider_missing_session(self) -> None:
        assert not self.manager.set_provider("nonexistent", "p1")

    def test_record_task(self) -> None:
        session = self.manager.create_session()
        task = self.manager.record_task(
            session.session_id,
            task_id="t1",
            capability_id="codegen.nextjs",
            provider_id="anthropic.claude",
            agent_id="claude-code",
            goal="Build login page",
        )
        assert task is not None
        assert task.task_id == "t1"
        assert task.capability_id == "codegen.nextjs"
        assert task.goal == "Build login page"

    def test_record_task_missing_session(self) -> None:
        assert self.manager.record_task("nonexistent", "t1") is None

    def test_update_task(self) -> None:
        session = self.manager.create_session()
        self.manager.record_task(session.session_id, task_id="t1")

        result = ExecutionResult(task_id="t1", success=True, output="done")
        updated = self.manager.update_task(session.session_id, "t1", status="completed", result=result)
        assert updated is not None
        assert updated.status == "completed"
        assert updated.result.success

    def test_update_task_missing_session(self) -> None:
        assert self.manager.update_task("nonexistent", "t1") is None

    def test_get_task(self) -> None:
        session = self.manager.create_session()
        self.manager.record_task(session.session_id, task_id="t1")
        task = self.manager.get_task(session.session_id, "t1")
        assert task is not None
        assert task.task_id == "t1"

    def test_get_task_missing(self) -> None:
        session = self.manager.create_session()
        assert self.manager.get_task(session.session_id, "nonexistent") is None

    def test_get_task_history(self) -> None:
        session = self.manager.create_session()
        self.manager.record_task(session.session_id, task_id="t1")
        self.manager.record_task(session.session_id, task_id="t2")
        history = self.manager.get_task_history(session.session_id)
        assert len(history) == 2

    def test_add_artifact(self) -> None:
        session = self.manager.create_session()
        artifact = ArtifactReference(artifact_id="a1", name="output.txt", content_type="text/plain")
        assert self.manager.add_artifact(session.session_id, artifact)
        artifacts = self.manager.get_artifacts(session.session_id)
        assert len(artifacts) == 1
        assert artifacts[0].name == "output.txt"

    def test_get_artifacts_missing_session(self) -> None:
        assert self.manager.get_artifacts("nonexistent") == []

    def test_list_sessions(self) -> None:
        self.manager.create_session(project="p1")
        self.manager.create_session(project="p2")
        assert len(self.manager.list_sessions()) == 2

    def test_list_sessions_filter_by_state(self) -> None:
        s1 = self.manager.create_session()
        self.manager.create_session()
        self.manager.complete_session(s1.session_id)
        assert len(self.manager.list_sessions(state=SessionState.COMPLETED)) == 1

    def test_list_sessions_filter_by_project(self) -> None:
        self.manager.create_session(project="p1")
        self.manager.create_session(project="p2")
        assert len(self.manager.list_sessions(project="p1")) == 1

    def test_count(self) -> None:
        assert self.manager.count == 0
        self.manager.create_session()
        assert self.manager.count == 1

    def test_count_by_state(self) -> None:
        s1 = self.manager.create_session()
        self.manager.create_session()
        self.manager.complete_session(s1.session_id)
        counts = self.manager.count_by_state()
        assert counts.get("active") == 1
        assert counts.get("completed") == 1
