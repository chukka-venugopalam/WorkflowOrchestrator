"""Tests for WorkflowGenerator."""

from __future__ import annotations

import tempfile
from pathlib import Path

from workflow_orchestrator.builder.workflow_generator import WorkflowGenerator
from workflow_orchestrator.builder.data_models import TaskGraph, TaskNode, TaskPriority, TaskStatus

import yaml


class TestWorkflowGenerator:
    """Tests for WorkflowGenerator."""

    def setup_method(self) -> None:
        self.generator = WorkflowGenerator()
        self.temp_dir = tempfile.mkdtemp()

    def _create_graph(self) -> TaskGraph:
        graph = TaskGraph(graph_id="g1", project_id="p1")
        graph.phases = ["foundation", "features"]

        node1 = TaskNode(
            task_id="task_foundation_setup",
            name="Foundation Setup",
            phase="foundation",
            priority=TaskPriority.HIGH,
            status=TaskStatus.PENDING,
            capabilities_required=["tool.filesystem"],
            expected_outputs=["setup_complete"],
        )
        node2 = TaskNode(
            task_id="task_foundation_verify",
            name="Verify Foundation",
            phase="foundation",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.PENDING,
            dependencies=["task_foundation_setup"],
            capabilities_required=["verify.testing"],
            expected_outputs=["verification_report"],
        )
        graph.nodes["task_foundation_setup"] = node1
        graph.nodes["task_foundation_verify"] = node2
        return graph

    def test_generate_returns_paths(self) -> None:
        graph = self._create_graph()
        paths = self.generator.generate(graph, self.temp_dir)
        assert len(paths) > 0

    def test_generated_files_exist(self) -> None:
        graph = self._create_graph()
        paths = self.generator.generate(graph, self.temp_dir)
        for path in paths:
            assert Path(path).exists()

    def test_yaml_valid(self) -> None:
        graph = self._create_graph()
        paths = self.generator.generate(graph, self.temp_dir)
        for path in paths:
            with open(path) as f:
                data = yaml.safe_load(f)
            assert data is not None
            assert "name" in data
            assert "steps" in data

    def test_master_workflow_generated(self) -> None:
        graph = self._create_graph()
        paths = self.generator.generate(graph, self.temp_dir)
        master_paths = [p for p in paths if "master" in p]
        assert len(master_paths) > 0

    def test_phase_workflows_have_steps(self) -> None:
        graph = self._create_graph()
        paths = self.generator.generate(graph, self.temp_dir)
        phase_paths = [p for p in paths if "phase_" in p and "master" not in p]
        for path in phase_paths:
            with open(path) as f:
                data = yaml.safe_load(f)
            assert len(data.get("steps", [])) > 0
