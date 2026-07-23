"""Unit tests for WorkflowValidator."""

from __future__ import annotations

from workflow_orchestrator.execution.workflow_validator import WorkflowValidator, ValidationResult
from workflow_orchestrator.execution.workflow_compiler import ExecutionGraph, ExecutionNode
from workflow_orchestrator.models import WorkflowDefinition, WorkflowStep, OnFailure, RetryConfig


class TestWorkflowValidator:
    """Tests for the WorkflowValidator."""

    def setup_method(self) -> None:
        self.validator = WorkflowValidator()

    def test_valid_workflow(self) -> None:
        """Test that a valid workflow passes validation."""
        workflow = WorkflowDefinition(
            name="test",
            steps=[
                WorkflowStep(name="step_1", plugin="terminal", config={"command": "echo hello"}),
            ],
        )
        result = self.validator.validate(workflow)
        assert result.valid
        assert len(result.errors) == 0
        assert result.graph is not None
        assert len(result.graph.nodes) == 1

    def test_missing_name(self) -> None:
        """Test that missing workflow name generates an error."""
        workflow = WorkflowDefinition(
            name="",
            steps=[WorkflowStep(plugin="terminal", config={})],
        )
        result = self.validator.validate(workflow)
        assert not result.valid
        assert any("name" in e.lower() for e in result.errors)

    def test_empty_steps(self) -> None:
        """Test that empty steps generates an error."""
        workflow = WorkflowDefinition(name="test", steps=[])
        result = self.validator.validate(workflow)
        assert not result.valid
        assert any("steps" in e.lower() or "step" in e.lower() for e in result.errors)

    def test_missing_plugin(self) -> None:
        """Test that missing plugin generates an error."""
        workflow = WorkflowDefinition(
            name="test",
            steps=[WorkflowStep(config={})],
        )
        result = self.validator.validate(workflow)
        assert not result.valid
        assert any("plugin" in e.lower() for e in result.errors)

    def test_valid_on_failure_values(self) -> None:
        """Test that valid on_failure values are accepted."""
        workflow = WorkflowDefinition(
            name="test",
            steps=[
                WorkflowStep(
                    name="step_1",
                    plugin="terminal",
                    config={},
                    on_failure=OnFailure.CONTINUE,
                ),
            ],
        )
        result = self.validator.validate(workflow)
        assert result.valid

    def test_negative_retry(self) -> None:
        """Test that negative retry values generate errors."""
        workflow = WorkflowDefinition(
            name="test",
            steps=[
                WorkflowStep(
                    name="step_1",
                    plugin="terminal",
                    config={},
                    retry=RetryConfig(max_retries=-1),
                ),
            ],
        )
        result = self.validator.validate(workflow)
        assert not result.valid

    def test_self_referencing_dependency(self) -> None:
        """Test that self-referencing dependencies are detected."""
        graph = ExecutionGraph(
            workflow_id="wf-1",
            workflow_name="test",
            nodes={
                "step_1": ExecutionNode(node_id="step_1", step_index=1, plugin="terminal", depends_on=["step_1"]),
            },
        )
        from workflow_orchestrator.execution.workflow_compiler import ExecutionEdge
        graph.edges = [ExecutionEdge(from_node_id="step_1", to_node_id="step_1")]

        result = self.validator.validate_graph(graph)
        assert not result.valid
        assert any("self-referencing" in e.lower() for e in result.errors)

    def test_orphan_dependency(self) -> None:
        """Test that orphan dependency references are detected."""
        graph = ExecutionGraph(
            workflow_id="wf-1",
            workflow_name="test",
            nodes={
                "step_1": ExecutionNode(
                    node_id="step_1", step_index=1, plugin="terminal",
                    depends_on=["non_existent_step"],
                ),
            },
        )
        result = self.validator.validate_graph(graph)
        assert not result.valid
        assert any("unknown" in e.lower() or "non_existent" in str(e) for e in result.errors)

    def test_validate_graph_independent_nodes_warning(self) -> None:
        """Test that independent nodes generate a warning."""
        graph = ExecutionGraph(
            workflow_id="wf-1",
            workflow_name="test",
            nodes={
                "step_1": ExecutionNode(node_id="step_1", step_index=1, plugin="terminal"),
                "step_2": ExecutionNode(node_id="step_2", step_index=2, plugin="terminal"),
            },
        )
        result = self.validator.validate_graph(graph)
        assert result.valid
        assert any("independent" in w.lower() for w in result.warnings)
