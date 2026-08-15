"""Unit tests for ProjectFlowEngine task queue execution result evaluation (Bug 1 fix)."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from workflow_orchestrator.orchestrator.project_flow import ProjectFlowEngine, FlowExecutionRecord
from workflow_orchestrator.execution.parallel_task_queue import TaskProgressState


def test_project_flow_all_failed_tasks_returns_failed_status(tmp_path):
    """Assert that if all tasks in task_queue fail, FlowExecutionRecord.status is 'failed' and NOT 'completed'."""
    engine = ProjectFlowEngine()

    mock_build_result = {
        "success": True,
        "project_name": "test_failed_project",
        "duration_seconds": 1.23,
    }

    mock_queue_results = {
        "task_backend": TaskProgressState.FAILED,
        "task_frontend": TaskProgressState.FAILED,
        "task_tests": TaskProgressState.FAILED,
        "task_deployment": TaskProgressState.FAILED,
    }

    with patch.object(engine.builder, "build", return_value=mock_build_result):
        with patch("workflow_orchestrator.execution.parallel_task_queue.ParallelTaskQueue.execute_queue", return_value=mock_queue_results):
            rec = engine.execute_project_from_prompt(
                idea="Build a test app",
                project_name="test_failed_project",
                workspace_dir=tmp_path,
                auto_confirm=True,
            )

            assert rec.status != "completed"
            assert rec.status == "failed"
            assert len(rec.failed_tasks) == 4
            assert set(rec.failed_tasks) == {"task_backend", "task_frontend", "task_tests", "task_deployment"}
            assert "4/4 tasks failed" in rec.error


def test_project_flow_partial_failed_tasks_returns_partial_status(tmp_path):
    """Assert that if some tasks succeed and some fail, FlowExecutionRecord.status is 'partial'."""
    engine = ProjectFlowEngine()

    mock_build_result = {
        "success": True,
        "project_name": "test_partial_project",
        "duration_seconds": 2.34,
    }

    mock_queue_results = {
        "task_backend": TaskProgressState.COMPLETED,
        "task_frontend": TaskProgressState.COMPLETED,
        "task_tests": TaskProgressState.FAILED,
        "task_deployment": TaskProgressState.FAILED,
    }

    with patch.object(engine.builder, "build", return_value=mock_build_result):
        with patch("workflow_orchestrator.execution.parallel_task_queue.ParallelTaskQueue.execute_queue", return_value=mock_queue_results):
            rec = engine.execute_project_from_prompt(
                idea="Build a partial app",
                project_name="test_partial_project",
                workspace_dir=tmp_path,
                auto_confirm=True,
            )

            assert rec.status == "partial"
            assert len(rec.failed_tasks) == 2
            assert set(rec.failed_tasks) == {"task_tests", "task_deployment"}
            assert len(rec.succeeded_tasks) == 2
            assert set(rec.succeeded_tasks) == {"task_backend", "task_frontend"}
            assert "2/4 tasks did not complete" in rec.error
