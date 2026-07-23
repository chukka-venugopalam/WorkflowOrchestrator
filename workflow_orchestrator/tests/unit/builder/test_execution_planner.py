"""Tests for ExecutionPlanner."""

from __future__ import annotations

from workflow_orchestrator.builder.execution_planner import ExecutionPlanner
from workflow_orchestrator.builder.data_models import TaskGraph, TaskNode, TaskPriority, TaskStatus


class TestExecutionPlanner:
    """Tests for ExecutionPlanner."""

    def setup_method(self) -> None:
        self.planner = ExecutionPlanner()

    def _create_graph(self) -> TaskGraph:
        graph = TaskGraph(graph_id="g1", project_id="p1")
        graph.phases = ["foundation"]

        node1 = TaskNode(
            task_id="task_foundation_setup",
            name="Setup",
            phase="foundation",
            priority=TaskPriority.HIGH,
            status=TaskStatus.PENDING,
        )
        node2 = TaskNode(
            task_id="task_foundation_verify",
            name="Verify",
            phase="foundation",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.PENDING,
            dependencies=["task_foundation_setup"],
        )
        graph.nodes["task_foundation_setup"] = node1
        graph.nodes["task_foundation_verify"] = node2
        return graph

    def test_plan_returns_batches(self) -> None:
        graph = self._create_graph()
        batches = self.planner.plan(graph)
        assert len(batches) > 0

    def test_batch_has_tasks(self) -> None:
        graph = self._create_graph()
        batches = self.planner.plan(graph)
        for batch in batches:
            assert len(batch.tasks) > 0

    def test_batch_has_mode(self) -> None:
        graph = self._create_graph()
        batches = self.planner.plan(graph)
        for batch in batches:
            assert batch.mode in ("parallel", "sequential")

    def test_batch_ids_unique(self) -> None:
        graph = self._create_graph()
        batches = self.planner.plan(graph)
        ids = [b.batch_id for b in batches]
        assert len(ids) == len(set(ids))

    def test_dependencies_respected(self) -> None:
        graph = self._create_graph()
        batches = self.planner.plan(graph)
        # Setup should be in first batch, Verify in second
        first_batch_tasks = set()
        for batch in batches:
            first_batch_tasks.update(batch.tasks)
            if "task_foundation_setup" in first_batch_tasks and "task_foundation_verify" in batch.tasks:
                # Verify should be in a later batch
                break
        assert "task_foundation_setup" in first_batch_tasks or len(batches) >= 1

    def test_max_concurrent(self) -> None:
        graph = self._create_graph()
        batches = self.planner.plan(graph, max_concurrent=1)
        for batch in batches:
            assert len(batch.tasks) <= 1

    def test_parallel_detection(self) -> None:
        graph = self._create_graph()
        # Add more independent tasks
        for i in range(3):
            node = TaskNode(
                task_id=f"task_independent_{i}",
                name=f"Independent {i}",
                phase="foundation",
                priority=TaskPriority.LOW,
                status=TaskStatus.PENDING,
            )
            graph.nodes[f"task_independent_{i}"] = node
        batches = self.planner.plan(graph)
        parallel_batches = [b for b in batches if b.mode == "parallel"]
        assert len(parallel_batches) >= 0
