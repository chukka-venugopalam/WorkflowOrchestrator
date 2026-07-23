"""Unit tests for GoalAnalyzer."""

from __future__ import annotations

from workflow_orchestrator.decision.decision_models import (
    DecisionContext,
    ProjectPhase,
)
from workflow_orchestrator.decision.goal_analyzer import GoalAnalyzer


class TestGoalAnalyzer:
    """Tests for the GoalAnalyzer."""

    def setup_method(self) -> None:
        self.analyzer = GoalAnalyzer()

    def test_analyze_python_api(self) -> None:
        """Test analyzing a Python API goal."""
        caps = self.analyzer.analyze("build a python api with tests")
        assert "codegen.python" in caps
        assert "codegen.backend" in caps
        assert "verify.test" in caps

    def test_analyze_deploy(self) -> None:
        """Test analyzing a deployment goal."""
        caps = self.analyzer.analyze("deploy the site to production")
        assert "deploy.vercel" in caps

    def test_analyze_code_review(self) -> None:
        """Test analyzing a code review goal."""
        caps = self.analyzer.analyze("review the latest pull request")
        assert "reasoning.code-review" in caps

    def test_analyze_empty_goal(self) -> None:
        """Test analyzing an empty goal."""
        caps = self.analyzer.analyze("")
        assert caps == []

    def test_analyze_with_phase_context(self) -> None:
        """Test analyzing with project phase context."""
        context = DecisionContext(
            project_phase=ProjectPhase.CODING,
        )
        caps = self.analyzer.analyze("add a new feature", context=context)
        assert "codegen.general" in caps

    def test_analyze_with_failed_steps(self) -> None:
        """Test that failed steps add verification capabilities."""
        context = DecisionContext(
            project_phase=ProjectPhase.CODING,
            failed_steps=["build_step"],
        )
        caps = self.analyzer.analyze("fix the build", context=context)
        assert "verify.build" in caps

    def test_analyze_with_constraints(self) -> None:
        """Test that constraints influence capability detection."""
        context = DecisionContext(
            constraints=["must pass all tests", "use python"],
        )
        caps = self.analyzer.analyze("implement feature", context=context)
        assert "codegen.python" in caps or "verify.test" in caps

    def test_analyze_with_priorities(self) -> None:
        """Test priority-scored capability analysis."""
        priorities = self.analyzer.analyze_with_priorities("build and test a python api")
        assert "codegen.python" in priorities
        assert "verify.test" in priorities
        assert priorities["codegen.python"] >= 0.5
        assert priorities["verify.test"] >= 0.5

    def test_extract_constraints(self) -> None:
        """Test extracting constraints from a goal."""
        constraints = self.analyzer.extract_constraints(
            "build a system that must handle 1000 requests per second within 2 weeks"
        )
        assert len(constraints) >= 1
        assert any("must" in c.lower() for c in constraints) or \
               any("within" in c.lower() for c in constraints)

    def test_extract_constraints_no_keywords(self) -> None:
        """Test extracting constraints from a goal with no constraint keywords."""
        constraints = self.analyzer.extract_constraints("hello world")
        assert len(constraints) == 0

    def test_analyze_git_operations(self) -> None:
        """Test analyzing Git-related goals."""
        caps = self.analyzer.analyze("clone the repository and commit changes")
        assert "tool.git" in caps
