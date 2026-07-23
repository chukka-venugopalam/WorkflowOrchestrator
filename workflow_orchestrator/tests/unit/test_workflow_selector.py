"""Unit tests for WorkflowSelector."""

from __future__ import annotations

from workflow_orchestrator.decision.decision_models import (
    DecisionContext,
    ProjectPhase,
)
from workflow_orchestrator.decision.workflow_selector import WorkflowSelector


class TestWorkflowSelector:
    """Tests for the WorkflowSelector."""

    def setup_method(self) -> None:
        self.selector = WorkflowSelector()

    def test_select_for_goal_empty(self) -> None:
        """Test selecting workflow with empty goal."""
        context = DecisionContext()
        selection = self.selector.select_for_goal("", context)
        assert selection.workflow_name == ""

    def test_select_for_goal_build(self) -> None:
        """Test selecting workflow for a build goal."""
        context = DecisionContext(project_phase=ProjectPhase.CODING)
        selection = self.selector.select_for_goal("build the project", context)
        assert selection.workflow_name is not None
        assert selection.confidence > 0

    def test_select_for_goal_deploy(self) -> None:
        """Test selecting workflow for a deploy goal."""
        context = DecisionContext(project_phase=ProjectPhase.DEPLOYMENT)
        selection = self.selector.select_for_goal("deploy to production", context)
        assert selection.workflow_name is not None
        assert selection.confidence > 0

    def test_select_for_goal_with_capabilities(self) -> None:
        """Test selecting workflow with capability context."""
        context = DecisionContext(
            project_phase=ProjectPhase.CODING,
            available_capabilities=["verify.build", "verify.test"],
        )
        selection = self.selector.select_for_goal("build", context)
        assert selection.workflow_name is not None

    def test_select_for_phase(self) -> None:
        """Test selecting workflows compatible with a phase."""
        context = DecisionContext(project_phase=ProjectPhase.CODING)
        selections = self.selector.select_for_phase(ProjectPhase.CODING, context)
        assert len(selections) > 0
        assert all(s.workflow_name for s in selections)

    def test_select_for_phase_deployment(self) -> None:
        """Test selecting workflows for deployment phase."""
        context = DecisionContext()
        selections = self.selector.select_for_phase(ProjectPhase.DEPLOYMENT, context)
        assert len(selections) > 0
        assert any("deploy" in s.workflow_name.lower() for s in selections)

    def test_register_custom_workflow(self) -> None:
        """Test registering a custom workflow."""
        self.selector.register_workflow(
            name="custom-workflow",
            description="A custom test workflow",
            tags=["custom", "test"],
            capabilities=["tool.custom"],
            phases=["coding"],
            source="workflows/custom.yaml",
        )
        context = DecisionContext(project_phase=ProjectPhase.CODING)
        selection = self.selector.select_for_goal("test the custom workflow", context)
        # The custom workflow should be found
        assert any(wf["name"] == "custom-workflow" for wf in self.selector._workflows)

    def test_select_for_goal_unknown_phase(self) -> None:
        """Test selecting workflow with unknown phase."""
        context = DecisionContext(project_phase=ProjectPhase.UNKNOWN)
        selection = self.selector.select_for_goal("do something", context)
        # Should return a result with low confidence
        assert isinstance(selection.confidence, float)
