"""Tests for StateManager."""

from __future__ import annotations

import tempfile

from workflow_orchestrator.builder.state_manager import StateManager
from workflow_orchestrator.builder.data_models import ProjectState, PhaseState


class TestStateManager:
    """Tests for StateManager."""

    def setup_method(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.manager = StateManager(state_dir=self.temp_dir)

    def _create_state(self) -> ProjectState:
        state = ProjectState(project_id="p1", project_name="Test", status="initializing")
        state.phases["planning"] = PhaseState(phase="planning", status="pending")
        state.phases["executing"] = PhaseState(phase="executing", status="pending")
        return state

    def test_initialize(self) -> None:
        state = self._create_state()
        self.manager.initialize(state)
        assert self.manager.current_state is not None

    def test_initial_state_property(self) -> None:
        assert self.manager.current_state is None

    def test_transition_to(self) -> None:
        state = self._create_state()
        self.manager.initialize(state)
        self.manager.transition_to("executing")
        assert self.manager.current_state.current_phase == "executing"

    def test_update_status(self) -> None:
        state = self._create_state()
        self.manager.initialize(state)
        self.manager.update_status("running")
        assert self.manager.current_state.status == "running"

    def test_update_status_completed(self) -> None:
        state = self._create_state()
        self.manager.initialize(state)
        self.manager.update_status("completed")
        assert self.manager.current_state.completed_at != ""

    def test_record_completed_task(self) -> None:
        state = self._create_state()
        self.manager.initialize(state)
        self.manager.record_completed_task("t1", "executing")
        assert "t1" in state.phases["executing"].completed_tasks

    def test_record_failed_task(self) -> None:
        state = self._create_state()
        self.manager.initialize(state)
        self.manager.record_failed_task("t1", "executing")
        assert "t1" in state.phases["executing"].failed_tasks

    def test_record_artifact(self) -> None:
        state = self._create_state()
        self.manager.initialize(state)
        self.manager.record_artifact("art_1", "planning")
        assert "art_1" in state.phases["planning"].artifacts

    def test_get_statistics(self) -> None:
        state = self._create_state()
        self.manager.initialize(state)
        stats = self.manager.get_statistics()
        assert stats["project_id"] == "p1"
        assert stats["total_phases"] == 2

    def test_load_state(self) -> None:
        state = self._create_state()
        self.manager.initialize(state)
        loaded = self.manager.load("p1")
        assert loaded is not None
        assert loaded.project_id == "p1"

    def test_load_wrong_id(self) -> None:
        state = self._create_state()
        self.manager.initialize(state)
        loaded = self.manager.load("wrong_id")
        assert loaded is None

    def test_no_state(self) -> None:
        loaded = self.manager.load("nonexistent")
        assert loaded is None
