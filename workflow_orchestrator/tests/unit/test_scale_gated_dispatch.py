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

    def _execute_desktop_task(self, task_payload: Dict[str, Any]) -> DesktopWorkerTaskResult:
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


class FailingWorker(DesktopWorker):
    """Worker whose _execute_desktop_task raises an exception."""

    def __init__(self, worker_id: str, name: str) -> None:
        super().__init__(worker_id=worker_id, name=name, skills=["failing_skill"])
        self.state = WorkerState.IDLE

    def discover(self) -> bool:
        return True

    def _execute_desktop_task(self, task_payload: Dict[str, Any]) -> DesktopWorkerTaskResult:
        raise RuntimeError("Worker process crashed unexpectedly")


def test_failing_worker_retains_failed_state():
    """Verify that a worker whose task fails transitions to WorkerState.FAILED and remains FAILED."""
    registry = DesktopWorkerRegistry()
    worker = FailingWorker("failing_worker_1", "Failing Worker")
    registry.register_worker(worker)

    queue = ParallelTaskQueue(
        worker_registry=registry,
        workspace_observer=MockObserver(),
        project_scale=ProjectScale.STANDARD,
    )

    t1 = queue.add_task("task_fail", "Failing Task", "failing_skill", "Do fail")
    t1.max_retries = 1
    queue.execute_queue(workspace_dir=Path.cwd())

    # Confirm worker state remains WorkerState.FAILED and is NOT reset to IDLE
    assert worker.state == WorkerState.FAILED, f"Expected worker state FAILED, got {worker.state}"
    assert worker.failed_at is not None, "Expected failed_at timestamp to be set"


class RecoverableWorker(DesktopWorker):
    """Worker that fails initially, then passes discovery and succeeds after cooldown."""

    def __init__(self, worker_id: str, name: str) -> None:
        super().__init__(worker_id=worker_id, name=name, skills=["recovery_skill"])
        self.state = WorkerState.IDLE
        self.should_fail = True
        self.discovery_healthy = True

    def discover(self) -> bool:
        return self.discovery_healthy

    def _execute_desktop_task(self, task_payload: Dict[str, Any]) -> DesktopWorkerTaskResult:
        if self.should_fail:
            raise RuntimeError("Transient network blip")
        return DesktopWorkerTaskResult(success=True, output_text="Recovered execution")


def test_failed_worker_recovers_after_cooldown_and_discovery_check():
    """Verify FAILED worker is excluded initially, then re-selected after cooldown + discover() health check."""
    import time
    registry = DesktopWorkerRegistry()
    worker = RecoverableWorker("rec_worker_1", "Recoverable Worker")
    registry.register_worker(worker)

    queue = ParallelTaskQueue(
        worker_registry=registry,
        workspace_observer=MockObserver(),
        project_scale=ProjectScale.STANDARD,
        cooldown_seconds=30.0,
    )

    # 1. Fail worker
    t_fail = queue.add_task("task_1", "Task 1", "recovery_skill", "Prompt 1")
    t_fail.max_retries = 1
    queue.execute_queue(workspace_dir=Path.cwd())
    assert worker.state == WorkerState.FAILED
    assert worker.failed_at is not None

    t_next = queue.add_task("task_2", "Task 2", "recovery_skill", "Prompt 2")

    # 2. Immediately after fail: _select_worker returns None (cooldown active)
    selected_immediate = queue._select_worker(t_next)
    assert selected_immediate is None
    assert worker.state == WorkerState.FAILED

    # 3. Simulate cooldown expired, but discover() returns False -> no discoverable worker, raises RuntimeError, failed_at stays unchanged
    worker.failed_at = time.time() - 35.0
    worker.discovery_healthy = False
    old_failed_at = worker.failed_at
    with pytest.raises(RuntimeError):
        queue._select_worker(t_next)
    assert worker.state == WorkerState.FAILED
    assert worker.failed_at == old_failed_at

    # 4. Cooldown expired AND discover() returns True -> re-selected by selection logic
    worker.discovery_healthy = True
    worker.should_fail = False
    selected_recovered = queue._select_worker(t_next)
    assert selected_recovered == worker
    assert worker.state == WorkerState.BUSY
    assert worker.failed_at is None


