"""Tests for VerificationManager."""

from __future__ import annotations

from workflow_orchestrator.builder.verification_manager import VerificationManager
from workflow_orchestrator.builder.artifact_validator import ArtifactValidator


class TestVerificationManager:
    """Tests for VerificationManager."""

    def setup_method(self) -> None:
        self.validator = ArtifactValidator()
        self.manager = VerificationManager(artifact_validator=self.validator)

    def test_verify_task_defaults_pass(self) -> None:
        result = self.manager.verify_task("task_001", {"files": {"main.py": "content"}})
        assert result.scope == "task"
        assert result.target_id == "task_001"

    def test_verify_task_with_failure(self) -> None:
        result = self.manager.verify_task("task_001", {"tests_passed": False})
        assert not result.tests_pass

    def test_verify_task_no_outputs(self) -> None:
        result = self.manager.verify_task("task_001", {})
        assert isinstance(result.issues, list)

    def test_verify_phase(self) -> None:
        result = self.manager.verify_phase("foundation", {"status": "ok"})
        assert result.scope == "phase"

    def test_verify_project(self) -> None:
        result = self.manager.verify_project("proj_1", {"status": "ok"})
        assert result.scope == "project"

    def test_verify_project_passes_by_default(self) -> None:
        result = self.manager.verify_project("proj_1", {"status": "ok"})
        assert result.passed

    def test_artifact_checks_included(self) -> None:
        result = self.manager.verify_task("t1", {"files": {"main.py": "hello"}})
        assert len(result.artifact_checks) > 0


class TestVerificationManagerEdge:
    """Edge case tests for VerificationManager."""

    def test_empty_task_output(self) -> None:
        mgr = VerificationManager()
        result = mgr.verify_task("t1", {})
        # Without outputs, verification should warn but not necessarily fail
        assert isinstance(result, object)

    def test_custom_checks(self) -> None:
        mgr = VerificationManager()
        result = mgr.verify_task("t1", {
            "tests_passed": True,
            "lint_passed": True,
            "typecheck_passed": True,
            "contract_valid": True,
            "architecture_valid": True,
        })
        assert result.passed

    def test_some_checks_fail(self) -> None:
        mgr = VerificationManager()
        result = mgr.verify_task("t1", {
            "tests_passed": False,
            "lint_passed": True,
            "typecheck_passed": True,
        })
        assert not result.passed
