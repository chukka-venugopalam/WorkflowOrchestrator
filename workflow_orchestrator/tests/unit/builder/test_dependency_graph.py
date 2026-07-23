"""Tests for DependencyGraph."""

from __future__ import annotations

from workflow_orchestrator.builder.dependency_graph import DependencyGraph
from workflow_orchestrator.builder.data_models import TaskGraph, TaskNode, TaskStatus, TaskPriority


class TestDependencyGraph:
    """Tests for DependencyGraph."""

    def setup_method(self) -> None:
        self.dg = DependencyGraph()

    def _create_graph(self) -> TaskGraph:
        graph = TaskGraph(graph_id="g1", project_id="p1")
        graph.phases = ["phase1"]

        node_a = TaskNode(task_id="A", name="Task A", phase="phase1", priority=TaskPriority.HIGH)
        node_b = TaskNode(task_id="B", name="Task B", phase="phase1", priority=TaskPriority.HIGH, dependencies=["A"])
        node_c = TaskNode(task_id="C", name="Task C", phase="phase1", priority=TaskPriority.MEDIUM, dependencies=["A"])
        node_d = TaskNode(task_id="D", name="Task D", phase="phase1", priority=TaskPriority.LOW, dependencies=["B", "C"])

        graph.nodes = {"A": node_a, "B": node_b, "C": node_c, "D": node_d}
        return graph

    def test_load(self) -> None:
        graph = self._create_graph()
        self.dg.load(graph)
        assert self.dg.node_count == 4

    def test_get_dependencies(self) -> None:
        graph = self._create_graph()
        self.dg.load(graph)
        deps = self.dg.get_dependencies("D")
        assert sorted(deps) == ["B", "C"]

    def test_get_dependents(self) -> None:
        graph = self._create_graph()
        self.dg.load(graph)
        deps = self.dg.get_dependents("A")
        assert sorted(deps) == ["B", "C"]

    def test_get_all_dependencies(self) -> None:
        graph = self._create_graph()
        self.dg.load(graph)
        all_deps = self.dg.get_all_dependencies("D")
        assert all_deps == {"A", "B", "C"}

    def test_get_all_dependents(self) -> None:
        graph = self._create_graph()
        self.dg.load(graph)
        all_deps = self.dg.get_all_dependents("A")
        assert all_deps == {"B", "C", "D"}

    def test_no_cycles(self) -> None:
        graph = self._create_graph()
        self.dg.load(graph)
        assert not self.dg.has_cycles()

    def test_cycle_detection(self) -> None:
        graph = TaskGraph(project_id="p1")
        graph.nodes["A"] = TaskNode(task_id="A", name="A", dependencies=["B"])
        graph.nodes["B"] = TaskNode(task_id="B", name="B", dependencies=["A"])
        self.dg.load(graph)
        assert self.dg.has_cycles()

    def test_find_cycles(self) -> None:
        graph = TaskGraph(project_id="p1")
        graph.nodes["A"] = TaskNode(task_id="A", name="A", dependencies=["B"])
        graph.nodes["B"] = TaskNode(task_id="B", name="B", dependencies=["A"])
        self.dg.load(graph)
        cycles = self.dg.find_cycles()
        assert len(cycles) > 0

    def test_topological_sort(self) -> None:
        graph = self._create_graph()
        self.dg.load(graph)
        order = self.dg.topological_sort()
        assert len(order) == 4
        assert order.index("A") < order.index("B")
        assert order.index("A") < order.index("C")
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("D")

    def test_topological_sort_cycle_raises(self) -> None:
        graph = TaskGraph(project_id="p1")
        graph.nodes["A"] = TaskNode(task_id="A", name="A", dependencies=["B"])
        graph.nodes["B"] = TaskNode(task_id="B", name="B", dependencies=["A"])
        self.dg.load(graph)
        import pytest
        with pytest.raises(ValueError, match="cycles"):
            self.dg.topological_sort()

    def test_impact_analysis_low(self) -> None:
        graph = TaskGraph(project_id="p1")
        graph.nodes["A"] = TaskNode(task_id="A", name="Task A")
        self.dg.load(graph)
        impact = self.dg.impact_analysis("A")
        assert impact["impact_level"] == "low"

    def test_impact_analysis_medium(self) -> None:
        graph = self._create_graph()
        self.dg.load(graph)
        # A has 3 dependents (B, C, D) - medium impact (> 3 is high)
        impact = self.dg.impact_analysis("A")
        assert impact["impact_level"] == "medium"

    def test_critical_path(self) -> None:
        graph = self._create_graph()
        self.dg.load(graph)
        critical = self.dg.critical_path()
        assert len(critical) >= 1
        assert critical[0] == "A"

    def test_render_ascii(self) -> None:
        graph = self._create_graph()
        self.dg.load(graph)
        rendered = self.dg.render_ascii()
        assert "Task A" in rendered
        assert "Task D" in rendered

    def test_empty_graph(self) -> None:
        rendered = self.dg.render_ascii()
        assert "(empty graph)" in rendered

    def test_add_node(self) -> None:
        graph = TaskGraph(project_id="p1")
        self.dg.load(graph)
        self.dg.add_node(TaskNode(task_id="X", name="Task X"))
        assert self.dg.node_count == 1

    def test_remove_node(self) -> None:
        graph = self._create_graph()
        self.dg.load(graph)
        self.dg.remove_node("D")
        assert self.dg.node_count == 3

    def test_edge_count(self) -> None:
        graph = self._create_graph()
        self.dg.load(graph)
        assert self.dg.edge_count >= 3

    def test_get_path(self) -> None:
        graph = self._create_graph()
        self.dg.load(graph)
        path = self.dg.get_path("A", "D")
        assert len(path) >= 2

    def test_get_path_nonexistent(self) -> None:
        graph = self._create_graph()
        self.dg.load(graph)
        path = self.dg.get_path("A", "ZZZ")
        assert path == []
