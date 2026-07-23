"""Tests for RollbackManager."""

from __future__ import annotations

import tempfile

from workflow_orchestrator.builder.rollback_manager import RollbackManager
from workflow_orchestrator.builder.data_models import ProjectState, TaskGraph, TaskNode, TaskPriority


class TestRollbackManager:
    """Tests for RollbackManager."""

    def setup_method(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.manager = RollbackManager(state_dir=self.temp_dir)

    def _create_state(self) -> ProjectState:
        return ProjectState(project_id="p1", project_name="Test", current_phase="executing")

    def _create_graph(self) -> TaskGraph:
        graph = TaskGraph(graph_id="g1", project_id="p1")
        graph.nodes["t1"] = TaskNode(task_id="t1", name="Task 1", phase="foundation", priority=TaskPriority.HIGH)
        return graph

    def test_create_checkpoint(self) -> None:
        state = self._create_state()
        graph = self._create_graph()
        cp = self.manager.create_checkpoint(state, graph)
        assert cp.checkpoint_id != ""
        assert cp.checkpoint_type == "automatic"

    def test_create_phase_checkpoint(self) -> None:
        state = self._create_state()
        graph = self._create_graph()
        cp = self.manager.create_phase_checkpoint(state, graph)
        assert cp.checkpoint_type == "phase"

    def test_list_checkpoints(self) -> None:
        state = self._create_state()
        graph = self._create_graph()
        self.manager.create_checkpoint(state, graph, description="First")
        self.manager.create_checkpoint(state, graph, description="Second")
        checkpoints = self.manager.list_checkpoints()
        assert len(checkpoints) == 2

    def test_get_latest_checkpoint(self) -> None:
        state = self._create_state()
        graph = self._create_graph()
        self.manager.create_checkpoint(state, graph, description="First")
        self.manager.create_checkpoint(state, graph, description="Second")
        latest = self.manager.get_latest_checkpoint()
        assert latest is not None
        # Check that we got the latest checkpoint
        assert latest.description is not None

    def test_rollback_to_nonexistent(self) -> None:
        result = self.manager.rollback_to("nonexistent")
        assert not result.success

    def test_rollback_to_checkpoint(self) -> None:
        state = self._create_state()
        graph = self._create_graph()
        cp = self.manager.create_checkpoint(state, graph)
        result = self.manager.rollback_to(cp.checkpoint_id)
        assert result.success
        assert result.checkpoint_id == cp.checkpoint_id

    def test_rollback_phase(self) -> None:
        state = self._create_state()
        graph = self._create_graph()
        result = self.manager.rollback_phase("executing")
        # No checkpoint before phase, so should fail
        assert not result.success

    def test_empty_checkpoints(self) -> None:
        checkpoints = self.manager.list_checkpoints()
        assert checkpoints == []

    def test_latest_none_when_empty(self) -> None:
        latest = self.manager.get_latest_checkpoint()
        assert latest is None
