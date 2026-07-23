"""Tests for CompletionChecker."""

from __future__ import annotations

from workflow_orchestrator.builder.completion_checker import CompletionChecker
from workflow_orchestrator.builder.data_models import TaskGraph, TaskNode, TaskStatus, TaskPriority


class TestCompletionChecker:
    """Tests for CompletionChecker."""

    def setup_method(self) -> None:
        self.checker = CompletionChecker()

    def _create_graph(self) -> TaskGraph:
        graph = TaskGraph(graph_id="g1", project_id="p1")
        graph.phases = ["foundation"]
        node = TaskNode(
            task_id="task_001",
            name="Test Task",
            phase="foundation",
            priority=TaskPriority.HIGH,
            status=TaskStatus.COMPLETED,
            acceptance_criteria=["Criterion met"],
        )
        graph.nodes["task_001"] = node
        return graph

    def test_check_task_complete(self) -> None:
        graph = self._create_graph()
        status = self.checker.check_task("task_001", graph)
        assert status.scope == "task"
        assert status.target_id == "task_001"

    def test_check_task_not_found(self) -> None:
        graph = self._create_graph()
        status = self.checker.check_task("nonexistent", graph)
        assert not status.is_complete
        assert not status.can_proceed

    def test_check_task_pending(self) -> None:
        graph = self._create_graph()
        graph.nodes["task_001"].status = TaskStatus.PENDING
        status = self.checker.check_task("task_001", graph)
        assert not status.is_complete

    def test_check_phase(self) -> None:
        graph = self._create_graph()
        status = self.checker.check_phase("foundation", graph)
        assert status.scope == "phase"

    def test_check_phase_not_found(self) -> None:
        graph = TaskGraph(project_id="p1")
        status = self.checker.check_phase("nonexistent", graph)
        assert not status.is_complete

    def test_check_project(self) -> None:
        graph = self._create_graph()
        status = self.checker.check_project("p1", graph, ["foundation"])
        assert status.scope == "project"

    def test_check_project_not_complete(self) -> None:
        graph = self._create_graph()
        status = self.checker.check_project("p1", graph, [])
        assert not status.is_complete

    def test_check_project_with_contract(self) -> None:
        graph = self._create_graph()
        status = self.checker.check_project("p1", graph, [], {"status": "finalized"})
        assert "Contract finalized" in status.criteria_met

    def test_completion_percentage(self) -> None:
        graph = self._create_graph()
        status = self.checker.check_phase("foundation", graph)
        assert status.completion_percentage >= 0
