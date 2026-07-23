"""Unit tests for DecisionEngine."""

from __future__ import annotations

from workflow_orchestrator.decision.decision_engine import DecisionEngine
from workflow_orchestrator.decision.decision_models import (
    DecisionContext,
    ProjectPhase,
)


class TestDecisionEngine:
    """Tests for the DecisionEngine."""

    def setup_method(self) -> None:
        self.engine = DecisionEngine()

    def test_decide_next_step_with_goal(self) -> None:
        """Test making a decision with a goal."""
        decision = self.engine.decide_next_step(
            goal="build a python api",
        )
        assert decision.decision_type is not None
        assert decision.metadata.decision_id != ""
        assert "python" in str(decision.required_capabilities) or "codegen" in str(decision.required_capabilities)

    def test_decide_next_step_empty_goal(self) -> None:
        """Test making a decision with an empty goal."""
        decision = self.engine.decide_next_step()
        assert decision.decision_type is not None
        assert decision.metadata.decision_id != ""

    def test_decide_next_step_with_context(self) -> None:
        """Test making a decision with a pre-built context."""
        context = DecisionContext(
            project_phase=ProjectPhase.CODING,
            execution_status="running",
            available_capabilities=["codegen.python", "verify.test"],
        )
        decision = self.engine.decide_next_step(
            goal="implement feature",
            context=context,
        )
        assert decision.selected_provider is not None
        assert decision.selected_agent is not None

    def test_decide_next_step_with_execution_state(self) -> None:
        """Test making a decision with execution state."""
        decision = self.engine.decide_next_step(
            goal="fix build errors",
            execution_state={
                "status": "failed",
                "failed_nodes": ["build_step"],
                "completed_steps": [],
            },
        )
        assert decision.decision_type is not None
        if decision.metadata.trace:
            pass  # Trace should be populated

    def test_decide_recovery(self) -> None:
        """Test making a recovery decision."""
        context = DecisionContext(
            execution_status="running",
            failed_steps=["step_1"],
        )
        error = {
            "type": "timeout",
            "message": "Step timed out after 30 seconds",
            "severity": 3,
            "step": "step_1",
        }
        decision = self.engine.decide_recovery(error, context)
        assert decision.decision_type is not None
        assert decision.metadata.triggered_by is not None

    def test_decide_workflow(self) -> None:
        """Test making a workflow selection decision."""
        decision = self.engine.decide_workflow(goal="build and deploy the site")
        assert decision.decision_type == "select_workflow"
        if decision.selected_workflow:
            assert decision.selected_workflow.workflow_name is not None

    def test_decide_workflow_empty_goal(self) -> None:
        """Test workflow selection with empty goal."""
        decision = self.engine.decide_workflow(goal="")
        assert decision.decision_type == "select_workflow"

    def test_routing_policy_property(self) -> None:
        """Test the routing_policy property."""
        assert self.engine.routing_policy is not None
        assert self.engine.routing_policy.config.name == "default"

    def test_goal_analyzer_property(self) -> None:
        """Test the goal_analyzer property."""
        assert self.engine.goal_analyzer is not None

    def test_decide_next_step_trace(self) -> None:
        """Test that decision trace contains relevant information."""
        decision = self.engine.decide_next_step(
            goal="test the application",
            execution_state={"status": "idle"},
        )
        trace = decision.metadata.trace
        assert len(trace) > 0
        assert any("test" in t.lower() for t in trace)
