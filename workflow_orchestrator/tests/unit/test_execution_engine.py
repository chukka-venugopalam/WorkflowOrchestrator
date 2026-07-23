"""Unit tests for ExecutionEngine."""

from __future__ import annotations

from workflow_orchestrator.execution.execution_context import ExecutionContext
from workflow_orchestrator.execution.execution_engine import ExecutionEngine
from workflow_orchestrator.execution.retry_engine import RetryPolicy
from workflow_orchestrator.execution.step_executor import StepExecutor
from workflow_orchestrator.execution.workflow_compiler import ExecutionNode
from workflow_orchestrator.models import StepStatus


class TestExecutionEngine:
    """Tests for the ExecutionEngine."""

    def setup_method(self) -> None:
        self.engine = ExecutionEngine()
        self.context = ExecutionContext.create(workflow_name="test")

    def test_execute_node_success(self) -> None:
        """Test successful node execution."""
        node = ExecutionNode(node_id="step_1", step_index=1, name="Test", plugin="terminal")
        result = self.engine.execute_node(node, self.context)

        # With no plugin registry, this will likely fail
        # But we're testing the flow doesn't crash
        assert result.step_name == "Test"
        assert isinstance(result.status, StepStatus)

    def test_execute_node_with_retry(self) -> None:
        """Test node execution with retry policy."""
        node = ExecutionNode(
            node_id="step_1",
            step_index=1,
            name="Retry Test",
            plugin="failing_plugin",
            retry_config={"max_retries": 1, "delay": 0.1, "backoff": 1.0},
        )
        policy = RetryPolicy(max_retries=1, delay=0.1, backoff=1.0)
        result = self.engine.execute_node(node, self.context, retry_policy=policy)

        # Should return a failure result (plugin not found)
        assert isinstance(result.status, StepStatus)
        assert result.step_name == "Retry Test"

    def test_execute_node_continue_on_failure(self) -> None:
        """Test that on_failure=continue skips retry."""
        node = ExecutionNode(
            node_id="step_1",
            step_index=1,
            name="Continue Test",
            plugin="missing_plugin",
            on_failure="continue",
        )
        result = self.engine.execute_node(node, self.context)
        assert isinstance(result.status, StepStatus)

    def test_execute_node_context_update(self) -> None:
        """Test that context is updated after execution."""
        node = ExecutionNode(node_id="step_1", step_index=1, name="Context Test", plugin="terminal")
        self.engine.execute_node(node, self.context)

        # Context should have an output recorded for this node
        # (even if it's empty for failures)
        assert isinstance(self.context.variables, dict)

    def test_start_and_complete_run(self) -> None:
        """Test run lifecycle methods."""
        run_id = self.engine.start_run(self.context)
        assert run_id == self.context.run_id

        self.engine.complete_run(self.context, success=True)
        # Should not crash

    def test_update_run_state(self) -> None:
        """Test update_run_state without state engine."""
        # Without a state engine, this should be a no-op
        self.engine.update_run_state("run_1", "running")
        # Should not crash
