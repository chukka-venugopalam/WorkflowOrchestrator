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


import re

COMPLETION_MARKERS: List[str] = [
    "task complete",
    "task completed",
    "task finished",
    "completed successfully",
    "successfully completed",
    "execution complete",
    "all tasks complete",
]

COMPLETION_MARKER_REGEX = re.compile(
    r"\b(" + "|".join(re.escape(m) for m in COMPLETION_MARKERS) + r")\b",
    re.IGNORECASE,
)


def get_workspace_snapshot(workspace_dir: Path) -> Dict[Path, float]:
    """Capture mtime snapshot of all non-hidden files in workspace_dir."""
    snapshot: Dict[Path, float] = {}
    if workspace_dir.exists():
        for p in workspace_dir.rglob("*"):
            if p.is_file() and not any(part.startswith(".") for part in p.parts):
                try:
                    snapshot[p] = p.stat().st_mtime
                except OSError:
                    pass
    return snapshot


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
        """Execute assigned task payload via desktop transport with multi-turn conversation loop."""
        t0 = time.time()
        with self._execution_lock:
            self.state = WorkerState.BUSY
            try:
                result = self._execute_conversational_loop(task_payload)
                if result.success:
                    self.state = WorkerState.IDLE
                    self.failed_at = None
                else:
                    self.state = WorkerState.FAILED
                    self.failed_at = time.time()
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

    def _execute_conversational_loop(self, task_payload: Dict[str, Any]) -> DesktopWorkerTaskResult:
        """Execute task across multiple conversation turns until completion marker + file changes, or max_turns."""
        max_turns = int(task_payload.get("max_turns", 8))
        task_id = task_payload.get("task_id", "task")
        base_prompt = task_payload.get("prompt", "")
        workspace_dir = Path(task_payload.get("workspace_dir", Path.cwd()))

        accumulated_output: List[str] = []
        all_generated_files: List[Path] = []
        current_prompt = base_prompt

        initial_snapshot = get_workspace_snapshot(workspace_dir)
        turn_start_snapshot = initial_snapshot

        for turn in range(1, max_turns + 1):
            logger.info(
                f"Agent '{self.name}' turn {turn}/{max_turns}: sending prompt ({len(current_prompt)} chars)"
            )

            turn_payload = dict(task_payload)
            turn_payload["prompt"] = current_prompt
            turn_payload["turn"] = turn

            turn_result = self._execute_desktop_task(turn_payload)

            if not turn_result.success:
                logger.warning(f"Agent '{self.name}' turn {turn}/{max_turns} returned failure: {turn_result.error_message}")
                return turn_result

            resp_text = turn_result.output_text or ""
            accumulated_output.append(resp_text)
            if turn_result.generated_files:
                for gf in turn_result.generated_files:
                    if gf not in all_generated_files:
                        all_generated_files.append(gf)

            current_snapshot = get_workspace_snapshot(workspace_dir)
            files_changed_this_turn = any(
                p not in turn_start_snapshot or current_snapshot[p] > turn_start_snapshot[p]
                for p in current_snapshot
            ) or bool(turn_result.generated_files)

            files_changed_overall = any(
                p not in initial_snapshot or current_snapshot[p] > initial_snapshot[p]
                for p in current_snapshot
            ) or bool(all_generated_files)

            marker_found = bool(COMPLETION_MARKER_REGEX.search(resp_text))

            allow_no_file_changes = task_payload.get("allow_no_file_changes", False)
            force_single_turn = task_payload.get("force_single_turn", False)

            if force_single_turn:
                completion_detected = True
            elif allow_no_file_changes:
                completion_detected = marker_found
            else:
                completion_detected = marker_found and files_changed_overall

            logger.info(
                f"Agent '{self.name}' turn {turn}/{max_turns}: received response ({len(resp_text)} chars), "
                f"completion_detected={completion_detected}, files_changed={files_changed_this_turn}"
            )

            if completion_detected:
                new_disk_files = [p for p in current_snapshot if p not in initial_snapshot]
                for nf in new_disk_files:
                    if nf not in all_generated_files:
                        all_generated_files.append(nf)

                return DesktopWorkerTaskResult(
                    success=True,
                    output_text="\n\n".join(accumulated_output),
                    generated_files=all_generated_files,
                    metadata={
                        "worker": self.worker_id,
                        "turns_taken": turn,
                        "max_turns": max_turns,
                        "completion_detected": True,
                    },
                )

            if turn == max_turns:
                logger.warning(f"Agent '{self.name}' reached max turns ({max_turns}) without completion marker and file verification.")
                return DesktopWorkerTaskResult(
                    success=False,
                    output_text="\n\n".join(accumulated_output),
                    error_message=f"Task did not reach completion within {max_turns} turns",
                    generated_files=all_generated_files,
                    metadata={
                        "worker": self.worker_id,
                        "turns_taken": turn,
                        "max_turns": max_turns,
                        "completion_detected": False,
                    },
                )

            turn_start_snapshot = current_snapshot
            current_prompt = (
                f"[Agent Continuation Turn {turn + 1}]: Previous turn output:\n{resp_text}\n\n"
                f"Continue working on task '{task_id}'. Produce remaining code/artifacts and reply with 'TASK COMPLETE' when finished."
            )

        return DesktopWorkerTaskResult(
            success=False,
            error_message=f"Task did not reach completion within {max_turns} turns",
            output_text="\n\n".join(accumulated_output),
        )

    def _execute_desktop_task(self, task_payload: Dict[str, Any]) -> DesktopWorkerTaskResult:
        """Subclass override for desktop transport dispatch."""
        prompt = task_payload.get("prompt", "")
        return DesktopWorkerTaskResult(
            success=True,
            output_text=f"Processed prompt by {self.name}: {prompt[:100]} TASK COMPLETE",
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
