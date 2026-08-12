"""Parallel Task Queue — capability-based scheduling, progress tracking, parallel execution, and automatic retries across desktop workers.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from workflow_orchestrator.builder.data_models import ProjectScale
from workflow_orchestrator.workers.desktop_worker import DesktopWorker, WorkerState, DesktopWorkerTaskResult
from workflow_orchestrator.workers.worker_registry import DesktopWorkerRegistry
from workflow_orchestrator.integrations.workspace_observer import WorkspaceObserver

logger = logging.getLogger(__name__)


class TaskProgressState(str, Enum):
    QUEUED = "Queued"
    RUNNING = "Running"
    VERIFYING = "Verifying"
    COMPLETED = "Completed"
    FAILED = "Failed"


@dataclass
class OrchestrationTaskNode:
    """DAG Task Node in the Orchestrator task queue."""

    task_id: str
    title: str
    required_skill: str  # e.g., "backend_api", "frontend_ui", "unit_testing", "deployment"
    prompt: str
    dependencies: List[str] = field(default_factory=list)
    state: TaskProgressState = TaskProgressState.QUEUED
    assigned_worker_id: Optional[str] = None
    output_result: Optional[DesktopWorkerTaskResult] = None
    retry_count: int = 0
    max_retries: int = 3
    error_log: Optional[str] = None


class ParallelTaskQueue:
    """Manages multi-worker task execution, capability matching, progress tracking, and self-healing retries."""

    def __init__(
        self,
        worker_registry: Optional[DesktopWorkerRegistry] = None,
        workspace_observer: Optional[WorkspaceObserver] = None,
        project_scale: ProjectScale | str = ProjectScale.STANDARD,
    ) -> None:
        self.worker_registry = worker_registry or DesktopWorkerRegistry()
        self.observer = workspace_observer or WorkspaceObserver()
        if isinstance(project_scale, str):
            try:
                project_scale = ProjectScale(project_scale)
            except ValueError:
                project_scale = ProjectScale.STANDARD
        self.project_scale: ProjectScale = project_scale
        self.pinned_worker_id: Optional[str] = None
        self.tasks: Dict[str, OrchestrationTaskNode] = {}
        self.execution_log: List[Dict[str, Any]] = []
        self._worker_assignment_index: int = 0
        self._lock = threading.Lock()

    def add_task(
        self,
        task_id: str,
        title: str,
        required_skill: str,
        prompt: str,
        dependencies: Optional[List[str]] = None,
    ) -> OrchestrationTaskNode:
        """Add a new task node to the orchestration queue."""
        node = OrchestrationTaskNode(
            task_id=task_id,
            title=title,
            required_skill=required_skill,
            prompt=prompt,
            dependencies=dependencies or [],
        )
        self.tasks[task_id] = node
        logger.info(f"Task '{task_id}' queued with required skill '{required_skill}'.")
        return node

    def execute_queue(
        self,
        workspace_dir: Optional[Path] = None,
        max_total_seconds: float = 600.0,
    ) -> Dict[str, TaskProgressState]:
        """Execute all queued DAG tasks using capability matching, parallel dispatch, and verification."""
        workspace_path = workspace_dir or Path.cwd()
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > max_total_seconds:
                logger.warning(f"Pipeline timeout of {max_total_seconds}s exceeded after {elapsed:.1f}s. Halting queue execution.")
                with self._lock:
                    for t_id, t in self.tasks.items():
                        if t.state in (TaskProgressState.QUEUED, TaskProgressState.RUNNING):
                            t.state = TaskProgressState.FAILED
                            t.error_log = f"Pipeline timeout of {max_total_seconds}s exceeded"
                break

            with self._lock:
                ready_tasks = [
                    t for t in self.tasks.values()
                    if t.state == TaskProgressState.QUEUED and self._dependencies_completed(t)
                ]
                running_tasks = [
                    t for t in self.tasks.values()
                    if t.state in (TaskProgressState.RUNNING, TaskProgressState.VERIFYING)
                ]
                uncompleted = [t for t in self.tasks.values() if t.state != TaskProgressState.COMPLETED and t.state != TaskProgressState.FAILED]

            if not uncompleted:
                break

            if not ready_tasks and not running_tasks:
                logger.warning("No ready or running tasks in queue; halting queue execution.")
                break

            if not ready_tasks:
                time.sleep(0.05)
                continue

            dispatched_any = False
            if self.project_scale != ProjectScale.MINIMAL and len(ready_tasks) > 1:
                with ThreadPoolExecutor(max_workers=min(4, len(ready_tasks))) as executor:
                    futures = [
                        executor.submit(self._dispatch_and_verify_task, task, workspace_path, start_time)
                        for task in ready_tasks
                    ]
                    for f in futures:
                        if f.result():
                            dispatched_any = True
            else:
                for task in ready_tasks:
                    if (time.time() - start_time) > max_total_seconds:
                        logger.warning(f"Pipeline timeout of {max_total_seconds}s exceeded. Halting task dispatch.")
                        with self._lock:
                            task.state = TaskProgressState.FAILED
                            task.error_log = f"Pipeline timeout of {max_total_seconds}s exceeded"
                        break
                    if self._dispatch_and_verify_task(task, workspace_path, start_time):
                        dispatched_any = True

            if not dispatched_any:
                time.sleep(0.05)

        return {t_id: t.state for t_id, t in self.tasks.items()}

    def _dependencies_completed(self, task: OrchestrationTaskNode) -> bool:
        """Check if all parent dependency nodes are completed."""
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task.state != TaskProgressState.COMPLETED:
                return False
        return True

    def _select_worker(self, task: OrchestrationTaskNode) -> Optional[DesktopWorker]:
        """Select worker based on scale-gated execution strategy."""
        with self._lock:
            # MINIMAL scale: lock to first pinned worker if valid and available
            if self.project_scale == ProjectScale.MINIMAL and self.pinned_worker_id:
                pinned = self.worker_registry.get_worker(self.pinned_worker_id)
                if pinned and pinned.discover() and getattr(pinned, "state", WorkerState.IDLE) == WorkerState.IDLE:
                    pinned.state = WorkerState.BUSY
                    return pinned
                elif pinned and getattr(pinned, "state", WorkerState.IDLE) == WorkerState.BUSY:
                    return None

            # Capability-based worker selection & real discovery filtering
            eligible_workers = self.worker_registry.find_workers_by_skill(task.required_skill, active_only=True)
            installed_workers = [w for w in eligible_workers if w.discover()]

            if not installed_workers:
                installed_workers = [w for w in self.worker_registry.list_workers(active_only=True) if w.discover()]

            if not installed_workers:
                raise RuntimeError(
                    f"No installed or discoverable active desktop worker available for task '{task.task_id}' "
                    f"(required skill: '{task.required_skill}')."
                )

            # Strict IDLE-only matching: never double-book a worker that is already BUSY
            idle_workers = [w for w in installed_workers if getattr(w, "state", WorkerState.IDLE) == WorkerState.IDLE]
            if not idle_workers:
                return None

            if self.project_scale == ProjectScale.MINIMAL:
                selected = idle_workers[0]
                self.pinned_worker_id = selected.worker_id
                selected.state = WorkerState.BUSY
                return selected

            # STANDARD / LARGE scale: spread across IDLE matching workers
            selected = idle_workers[self._worker_assignment_index % len(idle_workers)]
            self._worker_assignment_index += 1
            selected.state = WorkerState.BUSY
            return selected

    def _dispatch_and_verify_task(
        self,
        task: OrchestrationTaskNode,
        workspace_dir: Path,
        queue_start_time: float = 0.0,
    ) -> bool:
        """Dispatch task to best available worker, verify output, and handle retries on failure."""
        with self._lock:
            if task.state != TaskProgressState.QUEUED:
                return False
            task.state = TaskProgressState.RUNNING

        worker = self._select_worker(task)
        if worker is None:
            with self._lock:
                task.state = TaskProgressState.QUEUED
            return False

        with self._lock:
            task.assigned_worker_id = worker.worker_id

        elapsed = time.time() - queue_start_time if queue_start_time > 0 else 0.0
        msg_start = (
            f"[Task Queue] Task '{task.task_id}' [{task.title}] starting (Attempt {task.retry_count + 1}) "
            f"on worker '{worker.name}' (Elapsed: {elapsed:.1f}s)"
        )
        logger.info(msg_start)
        print(f"  {msg_start}", flush=True)

        # 2. Worker Execution
        task_payload = {
            "task_id": task.task_id,
            "prompt": task.prompt,
            "workspace_dir": str(workspace_dir),
        }
        res = worker.execute(task_payload)

        with self._lock:
            task.output_result = res
            self.execution_log.append({
                "task_id": task.task_id,
                "worker_id": worker.worker_id,
                "success": res.success,
                "timestamp": time.time(),
            })

        if not res.success:
            msg_fail = f"[Task Queue] Task '{task.task_id}' execution failed: {res.error_message}"
            logger.warning(msg_fail)
            print(f"  {msg_fail}", flush=True)
            self._handle_task_retry(task, f"Worker execution error: {res.error_message}", workspace_dir)
            return True

        # 3. Verification Phase (State: Verifying)
        with self._lock:
            task.state = TaskProgressState.VERIFYING
        snapshot = self.observer.capture_snapshot()

        if snapshot.test_passed:
            with self._lock:
                task.state = TaskProgressState.COMPLETED
            msg_ok = f"[Task Queue] Task '{task.task_id}' successfully completed and verified."
            logger.info(msg_ok)
            print(f"  {msg_ok}", flush=True)
        else:
            msg_ver_fail = f"[Task Queue] Task '{task.task_id}' verification failed."
            logger.warning(msg_ver_fail)
            print(f"  {msg_ver_fail}", flush=True)
            self._handle_task_retry(task, f"Verification failed: {snapshot.last_test_output[:100]}", workspace_dir)
        return True

    def _handle_task_retry(self, task: OrchestrationTaskNode, error_msg: str, workspace_dir: Path) -> None:
        """Auto-retry task with prompt re-formulation or re-assignment."""
        task.retry_count += 1
        logger.warning(f"Task '{task.task_id}' failed (Attempt {task.retry_count}/{task.max_retries}): {error_msg}")

        if task.retry_count < task.max_retries:
            # Re-formulate prompt with error diagnostic
            task.prompt = f"{task.prompt}\n\n[RETRY FIX REQUIREMENT]: Previous run failed with error: {error_msg}. Please fix."
            task.state = TaskProgressState.QUEUED
        else:
            task.state = TaskProgressState.FAILED
            task.error_log = error_msg
            logger.error(f"Task '{task.task_id}' permanently failed after {task.max_retries} retries.")
