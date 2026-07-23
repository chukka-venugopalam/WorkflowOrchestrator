"""Tests for ProviderAssignment."""

from __future__ import annotations

from workflow_orchestrator.builder.provider_assignment import ProviderAssignment
from workflow_orchestrator.builder.data_models import TaskGraph, TaskNode, TaskPriority, TaskStatus


class TestProviderAssignment:
    """Tests for ProviderAssignment."""

    def setup_method(self) -> None:
        self.assignment = ProviderAssignment()

    def test_assign_returns_list(self) -> None:
        graph = TaskGraph(graph_id="g1", project_id="p1")
        graph.nodes["t1"] = TaskNode(task_id="t1", name="Task", phase="p1", priority=TaskPriority.HIGH)
        assignments = self.assignment.assign(graph)
        assert len(assignments) == 1

    def test_assign_has_task_id(self) -> None:
        graph = TaskGraph(graph_id="g1", project_id="p1")
        graph.nodes["t1"] = TaskNode(task_id="t1", name="Task", phase="p1", priority=TaskPriority.HIGH)
        assignments = self.assignment.assign(graph)
        assert assignments[0].task_id == "t1"

    def test_assign_empty_graph(self) -> None:
        graph = TaskGraph(graph_id="g1", project_id="p1")
        assignments = self.assignment.assign(graph)
        assert assignments == []

    def test_multiple_tasks(self) -> None:
        graph = TaskGraph(graph_id="g1", project_id="p1")
        for i in range(3):
            graph.nodes[f"t{i}"] = TaskNode(task_id=f"t{i}", name=f"Task {i}", phase="p1", priority=TaskPriority.MEDIUM)
        assignments = self.assignment.assign(graph)
        assert len(assignments) == 3

    def test_transport_default(self) -> None:
        graph = TaskGraph(graph_id="g1", project_id="p1")
        graph.nodes["t1"] = TaskNode(task_id="t1", name="Task", phase="p1", priority=TaskPriority.HIGH)
        assignments = self.assignment.assign(graph)
        assert assignments[0].transport == "rest_api"

    def test_empty_provider_when_no_engine(self) -> None:
        graph = TaskGraph(graph_id="g1", project_id="p1")
        graph.nodes["t1"] = TaskNode(task_id="t1", name="Task", phase="p1", priority=TaskPriority.HIGH)
        assignments = self.assignment.assign(graph)
        assert assignments[0].provider_id == ""
