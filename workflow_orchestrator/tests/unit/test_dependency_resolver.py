"""Unit tests for DependencyResolver."""

from __future__ import annotations

from workflow_orchestrator.execution.dependency_resolver import (
    DependencyResolver,
    ExecutionOrder,
    StepBatch,
)
from workflow_orchestrator.execution.workflow_compiler import (
    ExecutionEdge,
    ExecutionGraph,
    ExecutionNode,
)


class TestDependencyResolver:
    """Tests for the DependencyResolver."""

    def setup_method(self) -> None:
        self.resolver = DependencyResolver()

    def _make_graph(self, node_ids: list[str], edges: list[tuple[str, str]]) -> ExecutionGraph:
        nodes = {
            nid: ExecutionNode(node_id=nid, step_index=i, plugin="terminal")
            for i, nid in enumerate(node_ids, start=1)
        }
        graph_edges = [
            ExecutionEdge(from_node_id=f, to_node_id=t)
            for f, t in edges
        ]
        return ExecutionGraph(
            workflow_id="test",
            workflow_name="test",
            nodes=nodes,
            edges=graph_edges,
        )

    def test_resolve_no_dependencies(self) -> None:
        """Test resolution with no dependencies."""
        graph = self._make_graph(["step_1", "step_2", "step_3"], [])
        order = self.resolver.resolve(graph)

        assert not order.has_cycles
        assert len(order.node_ids) == 3
        assert len(order.parallel_groups) == 1  # All at the same level
        assert len(order.parallel_groups[0]) == 3

    def test_resolve_linear(self) -> None:
        """Test resolution of a linear dependency chain."""
        graph = self._make_graph(
            ["step_1", "step_2", "step_3"],
            [("step_1", "step_2"), ("step_2", "step_3")],
        )
        order = self.resolver.resolve(graph)

        assert not order.has_cycles
        assert order.node_ids == ["step_1", "step_2", "step_3"]
        assert len(order.parallel_groups) == 3
        assert order.parallel_groups[0] == ["step_1"]
        assert order.parallel_groups[1] == ["step_2"]
        assert order.parallel_groups[2] == ["step_3"]

    def test_resolve_diamond(self) -> None:
        """Test resolution of a diamond dependency graph."""
        # step_1 -> step_2 -> step_4
        # step_1 -> step_3 -> step_4
        graph = self._make_graph(
            ["step_1", "step_2", "step_3", "step_4"],
            [
                ("step_1", "step_2"),
                ("step_1", "step_3"),
                ("step_2", "step_4"),
                ("step_3", "step_4"),
            ],
        )
        order = self.resolver.resolve(graph)

        assert not order.has_cycles
        assert order.node_ids[0] == "step_1"
        assert order.node_ids[-1] == "step_4"
        # step_2 and step_3 can be parallel (level 1)
        assert order.levels["step_2"] == 1
        assert order.levels["step_3"] == 1
        assert order.levels["step_4"] == 2

    def test_resolve_cycle_detected(self) -> None:
        """Test that cycles are detected."""
        graph = self._make_graph(
            ["step_1", "step_2"],
            [("step_1", "step_2"), ("step_2", "step_1")],
        )
        order = self.resolver.resolve(graph)

        assert order.has_cycles
        assert len(order.cycle_paths) > 0

    def test_next_ready_batch_initial(self) -> None:
        """Test getting the initial ready batch (no completed steps)."""
        graph = self._make_graph(
            ["step_1", "step_2", "step_3"],
            [("step_1", "step_2"), ("step_2", "step_3")],
        )
        batch = self.resolver.next_ready_batch(graph, completed=set())

        assert batch.node_ids == ["step_1"]
        assert batch.can_parallelize is False  # Only one item
        assert batch.level == 0

    def test_next_ready_batch_after_completion(self) -> None:
        """Test getting the next ready batch after completing some steps."""
        graph = self._make_graph(
            ["step_1", "step_2", "step_3"],
            [("step_1", "step_2"), ("step_1", "step_3")],
        )
        batch = self.resolver.next_ready_batch(graph, completed={"step_1"})

        assert "step_2" in batch.node_ids
        assert "step_3" in batch.node_ids
        assert batch.can_parallelize is True

    def test_next_ready_batch_all_completed(self) -> None:
        """Test getting ready batch when all are completed."""
        graph = self._make_graph(
            ["step_1", "step_2"],
            [("step_1", "step_2")],
        )
        batch = self.resolver.next_ready_batch(graph, completed={"step_1", "step_2"})
        assert batch.node_ids == []

    def test_next_ready_batch_with_failed(self) -> None:
        """Test that failed steps are excluded from ready batch."""
        graph = self._make_graph(
            ["step_1", "step_2"],
            [("step_1", "step_2")],
        )
        batch = self.resolver.next_ready_batch(
            graph, completed=set(), failed={"step_1"}
        )
        assert batch.node_ids == []

    def test_conflicts_write_scope(self) -> None:
        """Test detection of write-scope conflicts."""
        graph = self._make_graph(["step_1", "step_2"], [])
        graph.nodes["step_1"].config["output"] = "same_file.txt"
        graph.nodes["step_2"].config["output"] = "same_file.txt"

        conflicts = self.resolver.conflicts(graph, ["step_1", "step_2"])
        assert len(conflicts) >= 1
        assert conflicts[0]["type"] == "write_scope_conflict"
        assert self.resolver.has_conflicts(graph, ["step_1", "step_2"])

    def test_no_conflicts_different_outputs(self) -> None:
        """Test no conflicts when steps write to different outputs."""
        graph = self._make_graph(["step_1", "step_2"], [])
        graph.nodes["step_1"].config["output"] = "file_a.txt"
        graph.nodes["step_2"].config["output"] = "file_b.txt"

        conflicts = self.resolver.conflicts(graph, ["step_1", "step_2"])
        assert len(conflicts) == 0
        assert not self.resolver.has_conflicts(graph, ["step_1", "step_2"])
