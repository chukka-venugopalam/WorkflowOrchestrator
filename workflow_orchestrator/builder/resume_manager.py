"""Resume Manager — supports resuming builder execution after various interruptions.

Supports:
- Resume after restart
- Resume after crash
- Resume after shutdown
- Resume from checkpoint
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.builder.data_models import (
    CheckpointRecord,
    ProjectState,
    RollbackResult,
    RollbackScope,
    TaskGraph,
)
from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class ResumeManager:
    """Manages resume of builder execution after interruptions.

    Detects the last known good state and provides mechanisms to
    resume execution from that point.

    Usage:
        >>> mgr = ResumeManager(state_dir="/path/to/.builder")
        >>> context = mgr.detect_resume_context()
        >>> if context["can_resume"]:
        ...     state = mgr.resume(context)
    """

    def __init__(
        self,
        state_dir: str | Path = ".builder",
        event_bus: EventBus | None = None,
    ) -> None:
        """Initialize the Resume Manager.

        Args:
            state_dir: Directory for state persistence.
            event_bus: Optional EventBus for publishing events.
        """
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # Resume detection
    # ------------------------------------------------------------------

    def detect_resume_context(self) -> dict[str, Any]:
        """Detect whether a resume is possible and what context is available.

        Returns:
            Dict with resume context information.
        """
        state_file = self._state_dir / "project_state.json"
        checkpoint_dir = self._state_dir / "checkpoints"

        context: dict[str, Any] = {
            "can_resume": False,
            "has_state": state_file.exists(),
            "has_checkpoints": checkpoint_dir.exists() and any(checkpoint_dir.iterdir()),
            "last_phase": "",
            "last_task": "",
            "checkpoint_id": "",
            "reason": "",
        }

        # Check for state
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text(encoding="utf-8"))
                context["last_phase"] = data.get("current_phase", "")
                context["project_id"] = data.get("project_id", "")
                context["project_name"] = data.get("project_name", "")
                context["has_state"] = True

                status = data.get("status", "")
                if status in ("completed", "failed"):
                    context["reason"] = f"Project already in terminal state: {status}"
                else:
                    context["can_resume"] = True
                    context["reason"] = f"Resume from phase: {context['last_phase']}"
            except (json.JSONDecodeError, OSError) as exc:
                context["reason"] = f"State file corrupted: {exc}"
        else:
            context["reason"] = "No state file found"

        # Check for checkpoints
        if context["has_checkpoints"]:
            latest = self._find_latest_checkpoint()
            if latest:
                context["checkpoint_id"] = latest.checkpoint_id
                context["checkpoint_phase"] = latest.phase
                context["checkpoint_timestamp"] = latest.timestamp

        return context

    def resume(self, resume_context: dict[str, Any]) -> ProjectState | None:
        """Resume execution from the detected context.

        Args:
            resume_context: The resume context from detect_resume_context().

        Returns:
            The restored ProjectState, or None.
        """
        project_state: ProjectState | None = None

        # Try checkpoint first
        if resume_context.get("checkpoint_id"):
            project_state = self.restore_from_checkpoint(resume_context["checkpoint_id"])

        # Fall back to state file
        if project_state is None and resume_context.get("has_state"):
            project_state = self._load_state_from_file()

        if project_state is None:
            logger.warning("No state available to resume")
            return None

        self._publish_event("builder.resumed", {
            "project_id": project_state.project_id,
            "phase": resume_context.get("last_phase", project_state.current_phase),
            "from_checkpoint": bool(resume_context.get("checkpoint_id")),
        })

        logger.info(
            "Resumed project '%s' at phase '%s'",
            project_state.project_name,
            resume_context.get("last_phase", project_state.current_phase),
        )
        return project_state

    def _load_state_from_file(self) -> ProjectState | None:
        """Load project state from the state file.

        Returns:
            The loaded ProjectState, or None.
        """
        state_file = self._state_dir / "project_state.json"
        if not state_file.exists():
            return None

        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            state = ProjectState(
                project_id=data.get("project_id", ""),
                project_name=data.get("project_name", ""),
                project_type=data.get("project_type", ""),
                status=data.get("status", ""),
                current_phase=data.get("current_phase", ""),
                started_at=data.get("started_at", ""),
                updated_at=data.get("updated_at", ""),
                completed_at=data.get("completed_at", ""),
                metadata=data.get("metadata", {}),
            )
            state.completed_phases = data.get("completed_phases", [])
            state.failed_phases = data.get("failed_phases", [])
            return state
        except (json.JSONDecodeError, OSError):
            return None

    # ------------------------------------------------------------------
    # Checkpoint-based resume
    # ------------------------------------------------------------------

    def restore_from_checkpoint(self, checkpoint_id: str) -> ProjectState | None:
        """Restore project state from a checkpoint.

        Args:
            checkpoint_id: The checkpoint identifier.

        Returns:
            The restored ProjectState, or None.
        """
        checkpoint = self._load_checkpoint(checkpoint_id)
        if checkpoint is None:
            return None

        state_data = checkpoint.project_state
        if not state_data:
            return None

        state = ProjectState(
            project_id=state_data.get("project_id", ""),
            project_name=state_data.get("project_name", ""),
            project_type=state_data.get("project_type", ""),
            status=state_data.get("status", ""),
            current_phase=state_data.get("current_phase", ""),
            started_at=state_data.get("started_at", ""),
            updated_at=datetime.now(timezone.utc).isoformat(),
            metadata=state_data.get("metadata", {}),
        )
        state.completed_phases = state_data.get("completed_phases", [])
        state.failed_phases = state_data.get("failed_phases", [])

        logger.info("Restored state from checkpoint '%s'", checkpoint_id)
        return state

    def restore_task_graph_from_checkpoint(self, checkpoint_id: str) -> TaskGraph | None:
        """Restore a task graph from a checkpoint.

        Args:
            checkpoint_id: The checkpoint identifier.

        Returns:
            The restored TaskGraph, or None.
        """
        checkpoint = self._load_checkpoint(checkpoint_id)
        if checkpoint is None:
            return None

        graph_data = checkpoint.task_graph
        if not graph_data:
            return None

        graph = TaskGraph(
            graph_id=graph_data.get("graph_id", ""),
            project_id=graph_data.get("project_id", ""),
            phases=graph_data.get("phases", []),
        )

        for tid, node_data in graph_data.get("nodes", {}).items():
            from workflow_orchestrator.builder.data_models import TaskNode
            node = TaskNode.from_dict(node_data)
            graph.nodes[tid] = node

        return graph

    # ------------------------------------------------------------------
    # Checkpoint management
    # ------------------------------------------------------------------

    def _find_latest_checkpoint(self) -> CheckpointRecord | None:
        """Find the latest checkpoint.

        Returns:
            The latest CheckpointRecord, or None.
        """
        checkpoint_dir = self._state_dir / "checkpoints"
        if not checkpoint_dir.exists():
            return None

        checkpoints = sorted(checkpoint_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not checkpoints:
            return None

        return self._load_checkpoint(checkpoints[0].stem)

    def _load_checkpoint(self, checkpoint_id: str) -> CheckpointRecord | None:
        """Load a checkpoint from disk.

        Args:
            checkpoint_id: The checkpoint identifier.

        Returns:
            The loaded CheckpointRecord, or None.
        """
        checkpoint_file = self._state_dir / "checkpoints" / f"{checkpoint_id}.json"
        if not checkpoint_file.exists():
            return None

        try:
            data = json.loads(checkpoint_file.read_text(encoding="utf-8"))
            return CheckpointRecord(
                checkpoint_id=data.get("checkpoint_id", checkpoint_id),
                timestamp=data.get("timestamp", ""),
                checkpoint_type=data.get("checkpoint_type", "automatic"),
                project_state=data.get("project_state", {}),
                task_graph=data.get("task_graph", {}),
                phase=data.get("phase", ""),
                task_id=data.get("task_id", ""),
                description=data.get("description", ""),
                artifact_hashes=data.get("artifact_hashes", {}),
            )
        except (json.JSONDecodeError, OSError):
            return None

    # ------------------------------------------------------------------
    # Crash detection
    # ------------------------------------------------------------------

    def detect_crash(self) -> bool:
        """Detect if the builder crashed during the last execution.

        Returns:
            True if a crash is detected.
        """
        crash_flag = self._state_dir / ".crash_flag"
        if not crash_flag.exists():
            return False

        try:
            flag_data = json.loads(crash_flag.read_text(encoding="utf-8"))
            return flag_data.get("crashed", False)
        except (json.JSONDecodeError, OSError):
            return False

    def set_crash_flag(self) -> None:
        """Set the crash detection flag."""
        self._state_dir.mkdir(parents=True, exist_ok=True)
        flag_data = {
            "crashed": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        (self._state_dir / ".crash_flag").write_text(json.dumps(flag_data), encoding="utf-8")

    def clear_crash_flag(self) -> None:
        """Clear the crash detection flag."""
        crash_flag = self._state_dir / ".crash_flag"
        if crash_flag.exists():
            crash_flag.unlink()

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(
                type=event_type, data=data, source="resume_manager",
            ))
        except Exception:
            pass
