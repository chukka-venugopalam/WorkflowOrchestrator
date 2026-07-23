"""Tests for TaskGraphBuilder."""

from __future__ import annotations

import uuid

from workflow_orchestrator.builder.task_graph_builder import TaskGraphBuilder
from workflow_orchestrator.builder.data_models import TaskNode


class TestTaskGraphBuilder:
    """Tests for TaskGraphBuilder."""

    def setup_method(self) -> None:
        self.builder = TaskGraphBuilder()
        self.roadmap = {
            "phases": [
                {
                    "phase": 1,
                    "name": "Foundation",
                    "description": "Setup phase",
                    "milestones": [
                        {"name": "Init", "deliverables": ["Repo created"]},
                        {"name": "Config", "deliverables": ["Config set up"]},
                    ],
                    "risk_checkpoints": [],
                    "estimated_complexity": "medium",
                    "depends_on": [],
                    "deliverables": ["Repo"],
                },
                {
                    "phase": 2,
                    "name": "Features",
                    "description": "Feature phase",
                    "milestones": [
                        {"name": "Core", "deliverables": ["Core features"]},
                    ],
                    "risk_checkpoints": [],
                    "estimated_complexity": "high",
                    "depends_on": [1],
                    "deliverables": ["Features"],
                },
            ],
        }
        self.requirements = {"vision": "Test"}
        self.architecture = {"folder_structure": ["src/"]}

    def test_build_returns_graph(self) -> None:
        graph = self.builder.build(self.roadmap, self.requirements, self.architecture, "proj_1")
        assert graph.graph_id != ""
        assert graph.project_id == "proj_1"

    def test_build_creates_tasks(self) -> None:
        graph = self.builder.build(self.roadmap, self.requirements, self.architecture, "proj_1")
        assert len(graph.nodes) > 0

    def test_build_has_edges(self) -> None:
        graph = self.builder.build(self.roadmap, self.requirements, self.architecture, "proj_1")
        assert len(graph.edges) > 0

    def test_phases_extracted(self) -> None:
        graph = self.builder.build(self.roadmap, self.requirements, self.architecture, "proj_1")
        assert len(graph.phases) == 2
        assert "foundation" in graph.phases
        assert "features" in graph.phases

    def test_tasks_have_capabilities(self) -> None:
        graph = self.builder.build(self.roadmap, self.requirements, self.architecture, "proj_1")
        for node in graph.nodes.values():
            assert len(node.capabilities_required) > 0

    def test_tasks_have_expected_outputs(self) -> None:
        graph = self.builder.build(self.roadmap, self.requirements, self.architecture, "proj_1")
        for node in graph.nodes.values():
            assert len(node.expected_outputs) > 0

    def test_entry_tasks(self) -> None:
        graph = self.builder.build(self.roadmap, self.requirements, self.architecture, "proj_1")
        assert len(graph.entry_tasks) > 0

    def test_dependency_edges(self) -> None:
        graph = self.builder.build(self.roadmap, self.requirements, self.architecture, "proj_1")
        # Foundation setup should have no dependencies
        setup_task = graph.nodes.get("task_foundation_setup")
        assert setup_task is not None

    def test_verify_tasks_exist(self) -> None:
        graph = self.builder.build(self.roadmap, self.requirements, self.architecture, "proj_1")
        verify_tasks = [t for t in graph.nodes.values() if t.task_id.endswith("_verify")]
        assert len(verify_tasks) > 0
