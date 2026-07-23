"""Tests for DeploymentPlanner."""

from __future__ import annotations

from workflow_orchestrator.builder.deployment_planner import DeploymentPlanner


class TestDeploymentPlanner:
    """Tests for DeploymentPlanner."""

    def setup_method(self) -> None:
        self.planner = DeploymentPlanner()

    def test_plan_returns_plan(self) -> None:
        plan = self.planner.plan({"technology_stack": {}, "deployment": {}}, "p1")
        assert plan.plan_id != ""
        assert plan.project_id == "p1"

    def test_hosting_determined(self) -> None:
        plan = self.planner.plan({
            "technology_stack": {"framework": "Next.js"},
            "deployment": {"hosting": ""},
        }, "p1")
        assert plan.hosting_platform != ""

    def test_env_vars_generated(self) -> None:
        plan = self.planner.plan({"technology_stack": {}, "deployment": {}}, "p1")
        assert len(plan.environment_variables) > 0

    def test_secrets_generated(self) -> None:
        plan = self.planner.plan({"technology_stack": {}, "deployment": {}}, "p1")
        assert len(plan.secrets) > 0

    def test_cicd_config(self) -> None:
        plan = self.planner.plan({"technology_stack": {}, "deployment": {}}, "p1")
        assert plan.ci_cd_config != ""

    def test_monitoring_config(self) -> None:
        plan = self.planner.plan({"technology_stack": {}, "deployment": {}}, "p1")
        assert plan.monitoring_config != ""

    def test_rollback_config(self) -> None:
        plan = self.planner.plan({"technology_stack": {}, "deployment": {}}, "p1")
        assert plan.rollback_config != ""

    def test_scaling_config(self) -> None:
        plan = self.planner.plan({"technology_stack": {}, "deployment": {}}, "p1")
        assert plan.scaling_config != ""

    def test_additional_steps(self) -> None:
        plan = self.planner.plan({"technology_stack": {}, "deployment": {}}, "p1")
        assert len(plan.additional_steps) > 0

    def test_nextjs_hosting(self) -> None:
        plan = self.planner.plan({"technology_stack": {"framework": "Next.js"}, "deployment": {}}, "p1")
        assert "Vercel" in plan.hosting_platform

    def test_django_hosting(self) -> None:
        plan = self.planner.plan({"technology_stack": {"framework": "Django"}, "deployment": {}}, "p1")
        assert "Railway" in plan.hosting_platform or "Heroku" in plan.hosting_platform
