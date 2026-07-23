"""Unit tests for WorkflowCompiler."""

from __future__ import annotations

from workflow_orchestrator.execution.workflow_compiler import (
    ExecutionEdge,
    ExecutionGraph,
    ExecutionNode,
    WorkflowCompiler,
)
from workflow_orchestrator.models import WorkflowDefinition, WorkflowStep, OnFailure, RetryConfig


class TestWorkflowCompiler:
    """Tests for the WorkflowCompiler."""

    def setup_method(self) -> None:
        self.compiler = WorkflowCompiler()

    def _make_workflow(
        self,
        name: str = "test",
        step_count: int = 1,
    ) -> WorkflowDefinition:
        steps = [
            WorkflowStep(
                name=f"Step {i}",
                plugin="terminal",
                config={"command": f"echo {i}"},
            )
            for i in range(1, step_count + 1)
        ]
        return WorkflowDefinition(name=name, steps=steps)

    def test_compile_empty_workflow_raises(self) -> None:
        """Test that empty workflows raise ValueError."""
        workflow = self._make_workflow(step_count=0)
        import pytest
        with pytest.raises(ValueError, match="no steps"):
            self.compiler.compile(workflow)

    def test_compile_single_step(self) -> None:
        """Test compiling a single-step workflow."""
        workflow = self._make_workflow(step_count=1)
        graph = self.compiler.compile(workflow)

        assert len(graph.nodes) == 1
        assert graph.workflow_name == "test"
        assert "step_1" in graph.nodes

        node = graph.nodes["step_1"]
        assert node.plugin == "terminal"
        assert node.status == "pending"
        assert node.depends_on == []

    def test_compile_multi_step(self) -> None:
        """Test compiling a multi-step workflow."""
        workflow = self._make_workflow(step_count=3)
        graph = self.compiler.compile(workflow)

        assert len(graph.nodes) == 3
        assert len(graph.edges) == 0  # No dependencies declared
        assert len(graph.entry_nodes) == 3  # All are entry nodes
        assert len(graph.terminal_nodes) == 3  # All are terminal nodes

    def test_compile_with_dependencies(self) -> None:
        """Test compiling with explicit dependencies."""
        workflow = self._make_workflow(step_count=3)
        workflow.steps[1].config["depends_on"] = ["step_1"]
        workflow.steps[2].config["depends_on"] = ["step_1", "step_2"]

        graph = self.compiler.compile(workflow)

        assert len(graph.nodes) == 3
        assert len(graph.edges) == 3

        # Check edges
        edge_pairs = {(e.from_node_id, e.to_node_id) for e in graph.edges}
        assert ("step_1", "step_2") in edge_pairs
        assert ("step_1", "step_3") in edge_pairs
        assert ("step_2", "step_3") in edge_pairs

        # Entry and terminal nodes
        assert graph.entry_nodes == ["step_1"]
        assert "step_3" in graph.terminal_nodes

    def test_compile_with_depends_on_alias(self) -> None:
        """Test that 'dependsOn' alias is supported."""
        workflow = self._make_workflow(step_count=2)
        workflow.steps[1].config["dependsOn"] = ["step_1"]

        graph = self.compiler.compile(workflow)
        assert len(graph.edges) == 1

    def test_compile_with_name_dependency(self) -> None:
        """Test resolving dependencies by step name."""
        workflow = WorkflowDefinition(
            name="named-deps",
            steps=[
                WorkflowStep(name="checkout", plugin="terminal", config={"command": "git clone"}),
                WorkflowStep(name="install", plugin="terminal", config={"command": "npm install", "depends_on": "checkout"}),
            ],
        )
        graph = self.compiler.compile(workflow)
        assert len(graph.edges) == 1
        assert graph.nodes["step_2"].depends_on == ["step_1"]

    def test_compile_node_attributes(self) -> None:
        """Test that node attributes are correctly set from step config."""
        workflow = WorkflowDefinition(
            name="attrs",
            steps=[
                WorkflowStep(
                    name="test step",
                    plugin="custom_plugin",
                    config={"key": "value"},
                    on_failure=OnFailure.CONTINUE,
                    retry=RetryConfig(max_retries=3, delay=2.0, backoff=1.5),
                ),
            ],
        )
        graph = self.compiler.compile(workflow)
        node = graph.nodes["step_1"]
        assert node.name == "test step"
        assert node.plugin == "custom_plugin"
        assert node.config.get("key") == "value"
        assert node.on_failure == "continue"
        assert node.retry_config["max_retries"] == 3
        assert node.retry_config["delay"] == 2.0
        assert node.retry_config["backoff"] == 1.5

    def test_execution_graph_dataclass(self) -> None:
        """Test ExecutionGraph creation."""
        graph = ExecutionGraph(
            workflow_id="wf-1",
            workflow_name="test",
            description="A test workflow",
        )
        assert graph.workflow_id == "wf-1"
        assert graph.nodes == {}
        assert graph.edges == []
        assert graph.entry_nodes == []
        assert graph.terminal_nodes == []

    def test_execution_node_dataclass(self) -> None:
        """Test ExecutionNode creation."""
        node = ExecutionNode(
            node_id="step_1",
            step_index=1,
            name="First step",
            plugin="terminal",
        )
        assert node.status == "pending"
        assert node.depends_on == []

    def test_execution_edge_dataclass(self) -> None:
        """Test ExecutionEdge creation."""
        edge = ExecutionEdge(from_node_id="step_1", to_node_id="step_2")
        assert edge.type == "dependency"
