"""Tests for ProgressTracker."""

from __future__ import annotations

from workflow_orchestrator.builder.progress_tracker import ProgressTracker
from workflow_orchestrator.builder.data_models import TaskGraph, TaskNode, TaskPriority


class TestProgressTracker:
    """Tests for ProgressTracker."""

    def setup_method(self) -> None:
        self.tracker = ProgressTracker()

    def test_initial_snapshot(self) -> None:
        snapshot = self.tracker.get_snapshot()
        assert snapshot.completed_tasks == 0
        assert snapshot.failed_tasks == 0

    def test_record_completion(self) -> None:
        self.tracker.record_task_completion("t1", "claude", "agent1", 1000)
        snapshot = self.tracker.get_snapshot()
        assert snapshot.completed_tasks == 1

    def test_record_failure(self) -> None:
        self.tracker.record_task_failure("t1", "claude", "agent1")
        snapshot = self.tracker.get_snapshot()
        assert snapshot.failed_tasks == 1

    def test_record_retry(self) -> None:
        self.tracker.record_retry()
        snapshot = self.tracker.get_snapshot()
        assert snapshot.retries == 1

    def test_provider_usage(self) -> None:
        self.tracker.record_task_completion("t1", "claude", "", 100)
        self.tracker.record_task_completion("t2", "claude", "", 200)
        self.tracker.record_task_completion("t3", "gemini", "", 300)
        snapshot = self.tracker.get_snapshot()
        assert snapshot.provider_usage["claude"] == 2
        assert snapshot.provider_usage["gemini"] == 1

    def test_agent_usage(self) -> None:
        self.tracker.record_task_completion("t1", "", "agent1", 100)
        self.tracker.record_task_completion("t2", "", "agent1", 200)
        snapshot = self.tracker.get_snapshot()
        assert snapshot.agent_usage["agent1"] == 2

    def test_artifact_tracking(self) -> None:
        self.tracker.record_artifact_produced()
        self.tracker.record_artifact_produced()
        snapshot = self.tracker.get_snapshot()
        assert snapshot.artifacts_produced == 2

    def test_milestone_tracking(self) -> None:
        self.tracker.record_milestone_completed()
        snapshot = self.tracker.get_snapshot()
        assert snapshot.milestones_completed == 1

    def test_snapshot_with_graph(self) -> None:
        graph = TaskGraph(graph_id="g1", project_id="p1")
        graph.nodes["t1"] = TaskNode(task_id="t1", name="Task 1", phase="p1", priority=TaskPriority.HIGH)
        self.tracker.record_task_completion("t1", "", "", 100)
        snapshot = self.tracker.get_snapshot(graph)
        assert snapshot.total_tasks == 1

    def test_summary(self) -> None:
        graph = TaskGraph(graph_id="g1", project_id="p1")
        graph.nodes["t1"] = TaskNode(task_id="t1", name="Task 1", phase="p1", priority=TaskPriority.HIGH)
        self.tracker.record_task_completion("t1", "", "", 100)
        summary = self.tracker.get_summary(graph)
        assert "status" in summary
        assert "progress" in summary

    def test_start_timing(self) -> None:
        self.tracker.start_timing()
        snapshot = self.tracker.get_snapshot()
        assert snapshot.duration_seconds >= 0

    def test_contract_completion(self) -> None:
        self.tracker.record_task_completion("t1", "", "", 100)
        self.tracker.record_task_completion("t2", "", "", 100)
        self.tracker.record_task_failure("t3", "", "")
        snapshot = self.tracker.get_snapshot()
        assert snapshot.contract_completion > 0
