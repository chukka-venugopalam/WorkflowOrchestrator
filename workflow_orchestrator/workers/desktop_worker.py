"""DesktopWorker Abstraction Layer — standardized wrapper for local desktop AI tools.

Provides standardized OS process lifecycle hooks:
discover, start, execute, heartbeat, pause, resume, recover, stop.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class WorkerState(str, Enum):
    DISCOVERED = "discovered"
    STOPPED = "stopped"
    STARTING = "starting"
    IDLE = "idle"
    BUSY = "busy"
    PAUSED = "paused"
    RECOVERING = "recovering"
    FAILED = "failed"


@dataclass
class SkillCapability:
    """Capability / skill exposed by a desktop worker."""

    skill_name: str  # "backend_api", "frontend_ui", "unit_testing", "documentation", "deployment", "git_ops"
    confidence: float = 1.0
    supported_transports: List[str] = field(default_factory=list)


@dataclass
class DesktopWorkerTaskResult:
    """Result payload returned by a desktop worker task execution."""

    success: bool
    output_text: str = ""
    generated_files: List[Path] = field(default_factory=list)
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DesktopWorker:
    """Base wrapper class for local desktop AI workers operating without cloud APIs."""

    def __init__(
        self,
        worker_id: str,
        name: str,
        skills: Optional[List[str]] = None,
        transport_type: str = "terminal",
    ) -> None:
        self.worker_id = worker_id
        self.name = name
        self.transport_type = transport_type
        self.state = WorkerState.STOPPED
        self.skills: List[SkillCapability] = [
            SkillCapability(skill_name=s, supported_transports=[transport_type])
            for s in (skills or ["general_coding"])
        ]
        self.last_heartbeat_time: float = time.time()
        self.process_handle: Any = None
        self.failed_at: Optional[float] = None
        self._execution_lock = threading.Lock()

    def discover(self) -> bool:
        """Discover binary executable, local service, or window handle on desktop."""
        return True

    def start(self) -> bool:
        """Launch desktop worker process or automation driver."""
        self.state = WorkerState.IDLE
        self.failed_at = None
        self.last_heartbeat_time = time.time()
        logger.info(f"DesktopWorker '{self.worker_id}' started successfully.")
        return True

    def execute(self, task_payload: Dict[str, Any]) -> DesktopWorkerTaskResult:
        """Execute assigned task payload via desktop transport."""
        t0 = time.time()
        with self._execution_lock:
            self.state = WorkerState.BUSY
            try:
                result = self._execute_desktop_task(task_payload)
                self.state = WorkerState.IDLE
                self.failed_at = None
                result.duration_seconds = time.time() - t0
                return result
            except Exception as e:
                self.state = WorkerState.FAILED
                self.failed_at = time.time()
                logger.error(f"DesktopWorker '{self.worker_id}' execution error: {e}")
                return DesktopWorkerTaskResult(
                    success=False,
                    error_message=str(e),
                    duration_seconds=time.time() - t0,
                )

    def _execute_desktop_task(self, task_payload: Dict[str, Any]) -> DesktopWorkerTaskResult:
        """Subclass override for desktop transport dispatch."""
        prompt = task_payload.get("prompt", "")
        return DesktopWorkerTaskResult(
            success=True,
            output_text=f"Processed prompt by {self.name}: {prompt[:100]}",
        )

    def heartbeat(self) -> bool:
        """Monitor responsiveness of local worker process or driver."""
        is_responsive = self.state != WorkerState.FAILED
        if is_responsive:
            self.last_heartbeat_time = time.time()
        return is_responsive

    def pause(self) -> bool:
        """Pause worker task execution."""
        if self.state in (WorkerState.IDLE, WorkerState.BUSY):
            self.state = WorkerState.PAUSED
            logger.info(f"DesktopWorker '{self.worker_id}' paused.")
            return True
        return False

    def resume(self) -> bool:
        """Resume paused worker task execution."""
        if self.state == WorkerState.PAUSED:
            self.state = WorkerState.BUSY
            logger.info(f"DesktopWorker '{self.worker_id}' resumed.")
            return True
        return False

    def recover(self) -> bool:
        """Auto-restart worker process or driver on freeze or failure."""
        logger.warning(f"Recovering DesktopWorker '{self.worker_id}'...")
        self.stop()
        return self.start()

    def stop(self) -> bool:
        """Gracefully terminate worker process or automation driver."""
        self.state = WorkerState.STOPPED
        logger.info(f"DesktopWorker '{self.worker_id}' stopped.")
        return True
