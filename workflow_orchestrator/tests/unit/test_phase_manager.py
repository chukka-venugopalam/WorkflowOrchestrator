"""Unit tests for PhaseManager."""

from __future__ import annotations

from workflow_orchestrator.decision.decision_models import (
    DecisionContext,
    ProjectPhase,
)
from workflow_orchestrator.decision.phase_manager import PhaseManager


class TestPhaseManager:
    """Tests for the PhaseManager."""

    def setup_method(self) -> None:
        self.manager = PhaseManager()

    def test_determine_phase_no_info(self) -> None:
        """Test phase determination with no information."""
        phase = self.manager.determine_phase()
        assert phase == ProjectPhase.UNKNOWN

    def test_determine_phase_coding_goal(self) -> None:
        """Test phase determination from a coding goal."""
        phase = self.manager.determine_phase(goal="implement the login feature")
        assert phase == ProjectPhase.CODING

    def test_determine_phase_deploy_goal(self) -> None:
        """Test phase determination from a deployment goal."""
        phase = self.manager.determine_phase(goal="deploy to production")
        assert phase == ProjectPhase.DEPLOYMENT

    def test_determine_phase_verify_goal(self) -> None:
        """Test phase determination from a verification goal."""
        phase = self.manager.determine_phase(goal="run tests and verify quality")
        assert phase == ProjectPhase.VERIFICATION

    def test_determine_phase_with_completed_steps(self) -> None:
        """Test phase determination with completed steps."""
        phase = self.manager.determine_phase(
            goal="build the site",
            completed_steps=["step_1", "step_2"],
        )
        assert phase is not None

    def test_determine_phase_with_context(self) -> None:
        """Test phase determination with decision context."""
        context = DecisionContext(
            project_phase=ProjectPhase.CODING,
            execution_status="running",
            completed_steps=["checkout", "install"],
        )
        phase = self.manager.determine_phase(
            goal="continue development",
            context=context,
        )
        assert phase == ProjectPhase.CODING

    def test_valid_transition(self) -> None:
        """Test valid phase transitions."""
        assert self.manager.can_transition(ProjectPhase.DISCOVERY, ProjectPhase.PLANNING)
        assert self.manager.can_transition(ProjectPhase.CODING, ProjectPhase.VERIFICATION)
        assert self.manager.can_transition(ProjectPhase.VERIFICATION, ProjectPhase.DEPLOYMENT)

    def test_invalid_transition(self) -> None:
        """Test invalid phase transitions."""
        assert not self.manager.can_transition(ProjectPhase.DISCOVERY, ProjectPhase.DEPLOYMENT)
        assert not self.manager.can_transition(ProjectPhase.DEPLOYMENT, ProjectPhase.DISCOVERY)

    def test_same_phase_transition(self) -> None:
        """Test transitioning to the same phase."""
        assert self.manager.can_transition(ProjectPhase.CODING, ProjectPhase.CODING)

    def test_determine_phase_maintenance_goal(self) -> None:
        """Test phase determination from a maintenance goal."""
        phase = self.manager.determine_phase(goal="update dependencies and refactor")
        assert phase == ProjectPhase.MAINTENANCE

    def test_determine_phase_planning_goal(self) -> None:
        """Test phase determination from a planning goal."""
        phase = self.manager.determine_phase(goal="design the architecture")
        assert phase == ProjectPhase.PLANNING

    def test_determine_phase_failed_execution(self) -> None:
        """Test phase determination from failed execution."""
        context = DecisionContext(
            execution_status="failed",
            failed_steps=["build_step"],
        )
        phase = self.manager.determine_phase(context=context)
        assert phase is not None
        # Failed execution should favor CODING or VERIFICATION
        assert phase in (ProjectPhase.CODING, ProjectPhase.VERIFICATION)
