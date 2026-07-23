"""Unit tests for DecisionContext and DecisionContextBuilder."""

from __future__ import annotations

from workflow_orchestrator.decision.decision_context import DecisionContextBuilder
from workflow_orchestrator.decision.decision_models import (
    DecisionContext,
    ProjectPhase,
)


class TestDecisionContext:
    """Tests for DecisionContext."""

    def test_default_context(self) -> None:
        """Test default context values."""
        context = DecisionContext()
        assert context.project_phase == ProjectPhase.UNKNOWN
        assert context.execution_status == "idle"
        assert context.completed_steps == []
        assert context.failed_steps == []
        assert context.available_capabilities == []

    def test_context_with_values(self) -> None:
        """Test context with explicit values."""
        context = DecisionContext(
            project_phase=ProjectPhase.CODING,
            execution_status="running",
            completed_steps=["step_1"],
            failed_steps=["step_2"],
            available_capabilities=["codegen.python", "verify.test"],
        )
        assert context.project_phase == ProjectPhase.CODING
        assert context.execution_status == "running"
        assert context.completed_steps == ["step_1"]
        assert context.failed_steps == ["step_2"]


class TestDecisionContextBuilder:
    """Tests for DecisionContextBuilder."""

    def setup_method(self) -> None:
        self.builder = DecisionContextBuilder()

    def test_build_default(self) -> None:
        """Test building with defaults."""
        context = self.builder.build()
        assert context.project_phase == ProjectPhase.UNKNOWN
        assert context.execution_status == "idle"

    def test_build_with_string_phase(self) -> None:
        """Test building with string phase."""
        context = self.builder.build(project_phase="coding")
        assert context.project_phase == ProjectPhase.CODING

    def test_build_with_enum_phase(self) -> None:
        """Test building with enum phase."""
        context = self.builder.build(project_phase=ProjectPhase.VERIFICATION)
        assert context.project_phase == ProjectPhase.VERIFICATION

    def test_build_with_invalid_phase(self) -> None:
        """Test building with invalid string phase defaults to UNKNOWN."""
        context = self.builder.build(project_phase="nonexistent_phase")
        assert context.project_phase == ProjectPhase.UNKNOWN

    def test_build_from_workflow_state(self) -> None:
        """Test building from workflow state."""
        workflow_state = {
            "status": "running",
            "completed_nodes": ["step_1", "step_2"],
            "failed_nodes": [],
            "step_results": {"step_1": {"status": "success"}},
        }
        context = self.builder.build_from_workflow_state(
            workflow_state=workflow_state,
            project_phase=ProjectPhase.CODING,
        )
        assert context.execution_status == "running"
        assert context.completed_steps == ["step_1", "step_2"]
        assert context.failed_steps == []
        assert context.project_phase == ProjectPhase.CODING

    def test_update_context(self) -> None:
        """Test updating a context."""
        original = self.builder.build(execution_status="idle")
        updated = self.builder.update_context(original, execution_status="running")
        assert updated.execution_status == "running"
        assert original.execution_status == "idle"  # Original unchanged

    def test_update_context_project_phase(self) -> None:
        """Test updating project phase in context."""
        original = self.builder.build(project_phase="discovery")
        updated = self.builder.update_context(original, project_phase="coding")
        assert updated.project_phase == ProjectPhase.CODING
        assert original.project_phase == ProjectPhase.DISCOVERY
