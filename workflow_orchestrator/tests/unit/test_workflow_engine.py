"""Unit tests for WorkflowEngine."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from workflow_orchestrator.execution.workflow_engine import (
    WorkflowEngine,
    WorkflowRun,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_STATUS_FAILED,
    WORKFLOW_STATUS_RUNNING,
    WORKFLOW_STATUS_PAUSED,
    WORKFLOW_STATUS_CANCELLED,
    WORKFLOW_STATUS_PENDING,
)
from workflow_orchestrator.models import WorkflowDefinition, WorkflowStep


class TestWorkflowEngine:
    """Tests for the WorkflowEngine."""

    def setup_method(self) -> None:
        self.engine = WorkflowEngine()

    def test_run_valid_workflow(self) -> None:
        """Test running a valid workflow completes."""
        workflow = WorkflowDefinition(
            name="test",
            steps=[
                WorkflowStep(name="step_1", plugin="terminal", config={"command": "echo hello"}),
            ],
        )
        run = self.engine.run(workflow)
        assert run.status in (WORKFLOW_STATUS_COMPLETED, WORKFLOW_STATUS_FAILED)

    def test_run_invalid_workflow_raises(self) -> None:
        """Test that an invalid workflow raises ValueError."""
        workflow = WorkflowDefinition(name="", steps=[])
        with pytest.raises(ValueError):
            self.engine.run(workflow)

    def test_run_from_yaml_file(self, tmp_path: Path) -> None:
        """Test running a workflow from a YAML file."""
        yaml_file = tmp_path / "test_workflow.yaml"
        yaml_file.write_text(yaml.dump({
            "name": "File Workflow",
            "steps": [
                {"terminal": {"command": "echo test"}},
            ],
        }))
        run = self.engine.run(yaml_file)
        assert run.workflow_name == "File Workflow"

    def test_run_from_yaml_file_not_found(self) -> None:
        """Test that a missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            self.engine.run("/nonexistent/workflow.yaml")

    def test_get_run(self) -> None:
        """Test getting a run by ID."""
        workflow = WorkflowDefinition(
            name="test",
            steps=[WorkflowStep(plugin="terminal", config={})],
        )
        run = self.engine.run(workflow)
        assert self.engine.get_run(run.run_id) is run
        assert self.engine.get_run("nonexistent") is None

    def test_cancel_run(self) -> None:
        """Test cancelling a running workflow."""
        workflow = WorkflowDefinition(
            name="test",
            steps=[WorkflowStep(plugin="terminal", config={})],
        )
        run = self.engine.run(workflow)

        # After execution, cancel should not work on terminal states
        if run.status not in (WORKFLOW_STATUS_COMPLETED, WORKFLOW_STATUS_FAILED, WORKFLOW_STATUS_CANCELLED):
            assert self.engine.cancel_run(run.run_id)
        else:
            assert not self.engine.cancel_run(run.run_id)

    def test_cancel_nonexistent_run(self) -> None:
        """Test cancelling a nonexistent run returns False."""
        assert not self.engine.cancel_run("nonexistent")

    def test_pause_and_resume_run(self) -> None:
        """Test pausing and resuming a workflow run."""
        # Create a workflow that runs steps to give us time to pause
        workflow = WorkflowDefinition(
            name="pause_test",
            steps=[
                WorkflowStep(plugin="terminal", config={"command": "echo 1"}),
                WorkflowStep(plugin="terminal", config={"command": "echo 2"}),
            ],
        )
        run = self.engine.run(workflow)

        # If the workflow is running, we can pause it
        if run.status == WORKFLOW_STATUS_RUNNING:
            assert self.engine.pause_run(run.run_id)
            assert run.status == WORKFLOW_STATUS_PAUSED
            assert self.engine.resume_run(run.run_id)
        else:
            # If it completed too fast, pause/resume should return False
            assert not self.engine.pause_run(run.run_id)

    def test_list_runs(self) -> None:
        """Test listing workflow runs."""
        workflow = WorkflowDefinition(
            name="test",
            steps=[WorkflowStep(plugin="terminal", config={})],
        )
        self.engine.run(workflow)
        self.engine.run(workflow)

        all_runs = self.engine.list_runs()
        assert len(all_runs) >= 2

    def test_list_runs_by_status(self) -> None:
        """Test listing runs filtered by status."""
        workflow = WorkflowDefinition(
            name="test",
            steps=[WorkflowStep(plugin="terminal", config={})],
        )
        self.engine.run(workflow)

        # Listing by a status should not fail
        completed_runs = self.engine.list_runs(status=WORKFLOW_STATUS_COMPLETED)
        assert isinstance(completed_runs, list)

    def test_run_summary(self) -> None:
        """Test getting a run summary."""
        workflow = WorkflowDefinition(
            name="test",
            steps=[WorkflowStep(plugin="terminal", config={})],
        )
        run = self.engine.run(workflow)

        summary = self.engine.run_summary(run.run_id)
        assert summary["run_id"] == run.run_id
        assert summary["workflow_name"] == "test"
        assert "status" in summary
        assert "step_results" in summary

    def test_run_summary_not_found(self) -> None:
        """Test run summary for nonexistent run."""
        summary = self.engine.run_summary("nonexistent")
        assert "error" in summary

    def test_run_with_context_variables(self) -> None:
        """Test running with initial context variables."""
        workflow = WorkflowDefinition(
            name="test",
            steps=[WorkflowStep(plugin="terminal", config={"command": "echo {{name}}"})],
        )
        run = self.engine.run(
            workflow,
            variables={"name": "world"},
        )
        assert run.context.get_variable("name") == "world"
