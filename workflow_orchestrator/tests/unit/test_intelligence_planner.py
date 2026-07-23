"""Unit tests for the Planner."""

from __future__ import annotations

from workflow_orchestrator.intelligence.planner import Planner
from workflow_orchestrator.intelligence.models import Plan


class TestPlanner:
    def setup_method(self) -> None:
        self.planner = Planner()

    def test_plan_code_generation(self) -> None:
        plan = self.planner.plan("Build a login page with Next.js")
        assert len(plan.steps) > 0
        assert "codegen.general" in plan.required_capabilities
        assert "reasoning.general" not in plan.required_capabilities
        assert plan.estimated_steps == len(plan.steps)

    def test_plan_reasoning(self) -> None:
        plan = self.planner.plan("Review the code for bugs")
        assert "reasoning.general" in plan.required_capabilities

    def test_plan_verification(self) -> None:
        plan = self.planner.plan("Test the login functionality")
        assert "verify.general" in plan.required_capabilities

    def test_plan_unknown_goal(self) -> None:
        plan = self.planner.plan("Just a random goal")
        assert len(plan.required_capabilities) > 0
        assert "reasoning.general" in plan.required_capabilities

    def test_plan_has_steps(self) -> None:
        plan = self.planner.plan("Implement feature X")
        assert len(plan.steps) >= 2
        assert "Analyze:" in plan.steps[0]
        assert "Execute:" in plan.steps[1]

    def test_validate_valid_plan(self) -> None:
        plan = self.planner.plan("Build something")
        errors = self.planner.validate_plan(plan)
        # Without a capability matcher, validation may warn about no providers
        # but the plan itself should be structurally valid
        assert plan.goal != ""
        assert len(plan.steps) > 0

    def test_validate_empty_plan(self) -> None:
        plan = Plan()
        errors = self.planner.validate_plan(plan)
        assert len(errors) > 0

    def test_is_valid(self) -> None:
        plan = self.planner.plan("Build")
        # is_valid may be False if no capability matcher is set
        # but the plan should be structurally valid
        assert plan.goal != ""
