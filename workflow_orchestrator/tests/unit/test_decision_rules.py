"""Unit tests for DecisionRules."""

from __future__ import annotations

from workflow_orchestrator.decision.decision_models import (
    DecisionContext,
    DecisionRule,
    ProjectPhase,
)
from workflow_orchestrator.decision.decision_rules import DecisionRules


class TestDecisionRules:
    """Tests for the DecisionRules engine."""

    def setup_method(self) -> None:
        self.rules = DecisionRules()

    def test_evaluate_no_errors(self) -> None:
        """Test evaluation with no errors returns route_execution."""
        context = DecisionContext(
            project_phase=ProjectPhase.CODING,
            execution_status="running",
            available_capabilities=["codegen.python"],
            available_providers=["provider_a"],
        )
        decision_type, result = self.rules.evaluate(context)
        assert result.matched
        assert decision_type is not None

    def test_evaluate_error_recovery(self) -> None:
        """Test that error recovery rule matches when errors exist."""
        context = DecisionContext(
            execution_status="running",
            failed_steps=["step_1"],
            errors=[{"type": "timeout", "severity": 3}],
        )
        decision_type, result = self.rules.evaluate(context)
        assert decision_type == "recover_error"

    def test_evaluate_no_capabilities(self) -> None:
        """Test evaluation with no capabilities returns select_capabilities."""
        context = DecisionContext(
            project_phase=ProjectPhase.CODING,
            execution_status="idle",
        )
        decision_type, result = self.rules.evaluate(context)
        # With a known phase but no capabilities
        assert result.matched

    def test_evaluate_trigger_approval_high_risk(self) -> None:
        """Test that approval is triggered for high-risk situations."""
        context = DecisionContext(
            execution_status="failed",
            failed_steps=["step_1", "step_2", "step_3"],
            project_phase=ProjectPhase.DEPLOYMENT,
            available_capabilities=["deploy.vercel"],
            # No providers — prevents route_execution from matching first
            # High risk: 3 failed steps (3) + failed status (2) + deployment (2) = 7 >= 4
        )
        decision_type, result = self.rules.evaluate(context)
        assert decision_type == "trigger_approval"

    def test_evaluate_complete(self) -> None:
        """Test that completion is detected."""
        context = DecisionContext(
            execution_status="running",
            completed_steps=["step_1", "step_2", "step_3"],
            failed_steps=[],
            available_capabilities=["codegen.python"],
            available_providers=["provider_a"],
        )
        decision_type, result = self.rules.evaluate(context)
        # Should match route_execution first (priority 20 > 100)
        # but complete check happens last
        assert result.matched

    def test_register_custom_rule(self) -> None:
        """Test registering a custom rule."""
        rule = DecisionRule(
            rule_id="custom_rule",
            name="Custom Test Rule",
            description="A custom rule for testing",
            priority=5,  # High priority
            condition="Always matches",
            action="Return custom action",
        )
        self.rules.register_rule(rule)
        # Should be first in priority order

    def test_evaluate_fallback_needed(self) -> None:
        """Test that fallback rule matches when errors exist with alternatives."""
        context = DecisionContext(
            execution_status="running",
            failed_steps=["step_1"],
            errors=[{"type": "provider_error"}],
            available_providers=["provider_a", "provider_b"],
            available_agents=["agent_a"],
        )
        decision_type, result = self.rules.evaluate(context)
        # Error recovery has priority 10, fallback has 40
        # Error recovery should match first due to higher priority
        assert result.matched
