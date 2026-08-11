"""Unit tests for Scale-Gated Execution Strategy (Task 2 & Task 3).
"""

from pathlib import Path
from typing import Any, Dict
import pytest

from workflow_orchestrator.builder.data_models import ProjectScale
from workflow_orchestrator.execution.parallel_task_queue import ParallelTaskQueue, TaskProgressState
from workflow_orchestrator.workers.desktop_worker import DesktopWorker, DesktopWorkerTaskResult, WorkerState
from workflow_orchestrator.workers.worker_registry import DesktopWorkerRegistry


class MockGeneralWorker(DesktopWorker):
    """Mock worker with broad capabilities."""

    def __init__(self, worker_id: str, name: str, skills: list[str]) -> None:
        super().__init__(worker_id=worker_id, name=name, skills=skills)
        self.state = WorkerState.IDLE

    def discover(self) -> bool:
        return True

    def execute(self, task_payload: Dict[str, Any]) -> DesktopWorkerTaskResult:
        return DesktopWorkerTaskResult(
            success=True,
            output_text="Mock task output",
        )


class MockObserver:
    def capture_snapshot(self):
        class Snapshot:
            test_passed = True
            last_test_output = "OK"
        return Snapshot()


def test_minimal_scale_locks_pinned_worker():
    """Task 2: MINIMAL scale locks to the first pinned worker across 3+ tasks."""
    registry = DesktopWorkerRegistry()
    w1 = MockGeneralWorker("worker_claude_code", "Claude Code Worker", ["backend_api", "frontend_ui", "unit_testing", "general"])
    w2 = MockGeneralWorker("worker_codex", "Codex Worker", ["backend_api", "frontend_ui", "unit_testing", "general"])
    w3 = MockGeneralWorker("worker_freebuff", "FreeBuff Worker", ["backend_api", "frontend_ui", "unit_testing", "general"])
    registry.register_worker(w1)
    registry.register_worker(w2)
    registry.register_worker(w3)

    queue = ParallelTaskQueue(
        worker_registry=registry,
        workspace_observer=MockObserver(),
        project_scale=ProjectScale.MINIMAL,
    )

    t1 = queue.add_task("task_1", "Backend Task", "backend_api", "Build backend")
    t2 = queue.add_task("task_2", "Frontend Task", "frontend_ui", "Build frontend")
    t3 = queue.add_task("task_3", "Testing Task", "unit_testing", "Build tests")

    results = queue.execute_queue(workspace_dir=Path.cwd())

    assert results["task_1"] == TaskProgressState.COMPLETED
    assert results["task_2"] == TaskProgressState.COMPLETED
    assert results["task_3"] == TaskProgressState.COMPLETED

    # All 3 tasks MUST report the same assigned_worker_id
    worker_ids = [t1.assigned_worker_id, t2.assigned_worker_id, t3.assigned_worker_id]
    assert len(set(worker_ids)) == 1, f"Expected all 3 tasks to share identical worker_id, got: {worker_ids}"
    assert queue.pinned_worker_id == t1.assigned_worker_id


def test_standard_scale_spreads_tasks_across_multiple_workers():
    """Task 3: STANDARD/LARGE scale distributes tasks across >1 available matching worker."""
    registry = DesktopWorkerRegistry()
    w1 = MockGeneralWorker("worker_a", "Worker A", ["backend_api", "general"])
    w2 = MockGeneralWorker("worker_b", "Worker B", ["backend_api", "general"])
    w3 = MockGeneralWorker("worker_c", "Worker C", ["backend_api", "general"])
    registry.register_worker(w1)
    registry.register_worker(w2)
    registry.register_worker(w3)

    queue = ParallelTaskQueue(
        worker_registry=registry,
        workspace_observer=MockObserver(),
        project_scale=ProjectScale.STANDARD,
    )

    t1 = queue.add_task("task_1", "Task 1", "backend_api", "Build 1")
    t2 = queue.add_task("task_2", "Task 2", "backend_api", "Build 2")
    t3 = queue.add_task("task_3", "Task 3", "backend_api", "Build 3")
    t4 = queue.add_task("task_4", "Task 4", "backend_api", "Build 4")

    results = queue.execute_queue(workspace_dir=Path.cwd())

    assert all(r == TaskProgressState.COMPLETED for r in results.values())

    assigned_workers = [t1.assigned_worker_id, t2.assigned_worker_id, t3.assigned_worker_id, t4.assigned_worker_id]
    distinct_workers = set(assigned_workers)
    assert len(distinct_workers) > 1, f"Expected tasks to be spread across multiple workers, got: {assigned_workers}"
