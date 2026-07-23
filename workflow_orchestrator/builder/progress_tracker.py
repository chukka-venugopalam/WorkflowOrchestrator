"""Progress Tracker — tracks completed tasks, failed tasks, retries, duration, provider usage, agent usage, artifacts, milestone completion, and contract completion.

Provides real-time progress snapshots and statistics throughout the builder lifecycle.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from workflow_orchestrator.builder.data_models import (
    ProgressSnapshot,
    TaskGraph,
    TaskStatus,
)
from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Tracks and reports builder progress throughout the project lifecycle.

    Records metrics on task completion, failures, retries, duration,
    resource usage, and milestones.

    Usage:
        >>> tracker = ProgressTracker()
        >>> tracker.record_task_completion("task_001", "anthropic.claude", "claude-code", 5000)
        >>> snapshot = tracker.get_snapshot(task_graph)
        >>> print(snapshot.completed_tasks)
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Progress Tracker.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus
        self._completed_tasks: set[str] = set()
        self._failed_tasks: set[str] = set()
        self._retries: int = 0
        self._start_time: float = 0.0
        self._provider_usage: dict[str, int] = {}
        self._agent_usage: dict[str, int] = {}
        self._artifacts_produced: int = 0
        self._milestones_completed: int = 0
        self._task_durations: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_task_completion(
        self,
        task_id: str,
        provider_id: str = "",
        agent_id: str = "",
        duration_ms: float = 0.0,
    ) -> None:
        """Record a task as completed.

        Args:
            task_id: The completed task identifier.
            provider_id: The provider used.
            agent_id: The agent used.
            duration_ms: Execution duration in milliseconds.
        """
        self._completed_tasks.add(task_id)
        self._task_durations[task_id] = duration_ms

        if provider_id:
            self._provider_usage[provider_id] = self._provider_usage.get(provider_id, 0) + 1
        if agent_id:
            self._agent_usage[agent_id] = self._agent_usage.get(agent_id, 0) + 1

    def record_task_failure(
        self,
        task_id: str,
        provider_id: str = "",
        agent_id: str = "",
    ) -> None:
        """Record a task as failed.

        Args:
            task_id: The failed task identifier.
            provider_id: The provider used.
            agent_id: The agent used.
        """
        self._failed_tasks.add(task_id)

        if provider_id:
            self._provider_usage[provider_id] = self._provider_usage.get(provider_id, 0) + 1
        if agent_id:
            self._agent_usage[agent_id] = self._agent_usage.get(agent_id, 0) + 1

    def record_retry(self) -> None:
        """Record a retry event."""
        self._retries += 1

    def record_artifact_produced(self) -> None:
        """Record an artifact being produced."""
        self._artifacts_produced += 1

    def record_milestone_completed(self) -> None:
        """Record a milestone being completed."""
        self._milestones_completed += 1

    def start_timing(self) -> None:
        """Start the execution timer."""
        self._start_time = time.time()

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def get_snapshot(self, task_graph: TaskGraph | None = None) -> ProgressSnapshot:
        """Get a progress snapshot at the current point in time.

        Args:
            task_graph: Optional task graph for total task count.

        Returns:
            ProgressSnapshot with current metrics.
        """
        total_tasks = len(task_graph.nodes) if task_graph else 0
        elapsed = (time.time() - self._start_time) if self._start_time > 0 else 0.0

        snapshot = ProgressSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            completed_tasks=len(self._completed_tasks),
            failed_tasks=len(self._failed_tasks),
            total_tasks=total_tasks,
            retries=self._retries,
            duration_seconds=round(elapsed, 2),
            provider_usage=dict(self._provider_usage),
            agent_usage=dict(self._agent_usage),
            artifacts_produced=self._artifacts_produced,
            milestones_completed=self._milestones_completed,
            contract_completion=self._calculate_contract_completion(),
        )

        return snapshot

    def get_summary(self, task_graph: TaskGraph | None = None) -> dict[str, Any]:
        """Get a human-readable progress summary.

        Args:
            task_graph: Optional task graph for detailed task info.

        Returns:
            Dict with summary information.
        """
        snapshot = self.get_snapshot(task_graph)
        completion = 0.0
        if snapshot.total_tasks > 0:
            completion = (snapshot.completed_tasks / snapshot.total_tasks) * 100

        return {
            "status": "completed" if snapshot.failed_tasks == 0 and snapshot.completed_tasks == snapshot.total_tasks else "in_progress",
            "progress": f"{snapshot.completed_tasks}/{snapshot.total_tasks} tasks",
            "completion_percentage": round(completion, 1),
            "failed": snapshot.failed_tasks,
            "retries": snapshot.retries,
            "duration": f"{snapshot.duration_seconds:.1f}s",
            "providers": dict(snapshot.provider_usage),
            "agents": dict(snapshot.agent_usage),
            "artifacts": snapshot.artifacts_produced,
            "milestones": snapshot.milestones_completed,
        }

    def _calculate_contract_completion(self) -> float:
        """Calculate estimated contract completion percentage.

        Returns:
            Completion percentage (0-100).
        """
        total = len(self._completed_tasks) + len(self._failed_tasks)
        if total == 0:
            return 0.0
        return round((len(self._completed_tasks) / total) * 100, 1)

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(
                type=event_type, data=data, source="progress_tracker",
            ))
        except Exception:
            pass
