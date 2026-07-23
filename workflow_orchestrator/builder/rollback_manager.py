"""Rollback Manager — creates automatic checkpoints, supports rollback, and version recovery.

Creates checkpoints at configurable intervals and provides
rollback capability to restore project state to any checkpoint.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.builder.data_models import (
    CheckpointRecord,
    CheckpointType,
    ProjectState,
    RollbackResult,
    RollbackScope,
    TaskGraph,
    TaskStatus,
)
from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class RollbackManager:
    """Manages checkpoints and rollback operations for the builder.

    Creates checkpoints at configurable intervals (automatic, phase,
    milestone) and supports rolling back to any previous checkpoint.

    Usage:
        >>> mgr = RollbackManager(state_dir="/path/to/.builder")
        >>> checkpoint = mgr.create_checkpoint(state, graph, "phase")
        >>> result = mgr.rollback_to(checkpoint.checkpoint_id)
        >>> print(result.success)
    """

    def __init__(
        self,
        state_dir: str | Path = ".builder",
        event_bus: EventBus | None = None,
    ) -> None:
        """Initialize the Rollback Manager.

        Args:
            state_dir: Directory for checkpoint persistence.
            event_bus: Optional EventBus for publishing events.
        """
        self._state_dir = Path(state_dir)
        self._checkpoint_dir = self._state_dir / "checkpoints"
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # Checkpoint creation
    # ------------------------------------------------------------------

    def create_checkpoint(
        self,
        project_state: ProjectState,
        task_graph: TaskGraph,
        checkpoint_type: str = "automatic",
        description: str = "",
    ) -> CheckpointRecord:
        """Create a checkpoint of the current project state.

        Args:
            project_state: The current project state.
            task_graph: The current task graph.
            checkpoint_type: Type of checkpoint (automatic, phase, milestone, manual).
            description: Optional description.

        Returns:
            The created CheckpointRecord.
        """
        checkpoint = CheckpointRecord(
            checkpoint_id=uuid.uuid4().hex[:12],
            timestamp=datetime.now(timezone.utc).isoformat(),
            checkpoint_type=checkpoint_type,
            project_state=self._serialize_project_state(project_state),
            task_graph=self._serialize_task_graph(task_graph),
            phase=project_state.current_phase,
            description=description or f"Checkpoint at phase: {project_state.current_phase}",
        )

        # Persist checkpoint
        checkpoint_file = self._checkpoint_dir / f"{checkpoint.checkpoint_id}.json"
        checkpoint_file.write_text(
            json.dumps({
                "checkpoint_id": checkpoint.checkpoint_id,
                "timestamp": checkpoint.timestamp,
                "checkpoint_type": checkpoint.checkpoint_type,
                "project_state": checkpoint.project_state,
                "task_graph": checkpoint.task_graph,
                "phase": checkpoint.phase,
                "task_id": checkpoint.task_id,
                "description": checkpoint.description,
                "artifact_hashes": checkpoint.artifact_hashes,
            }, indent=2),
            encoding="utf-8",
        )

        self._publish_event("builder.checkpoint_created", {
            "checkpoint_id": checkpoint.checkpoint_id,
            "type": checkpoint_type,
            "phase": project_state.current_phase,
        })

        logger.info(
            "Created checkpoint '%s' (type: %s) at phase '%s'",
            checkpoint.checkpoint_id[:8],
            checkpoint_type,
            project_state.current_phase,
        )
        return checkpoint

    def create_phase_checkpoint(
        self,
        project_state: ProjectState,
        task_graph: TaskGraph,
    ) -> CheckpointRecord:
        """Create a checkpoint marking a phase boundary.

        Args:
            project_state: The current project state.
            task_graph: The current task graph.

        Returns:
            The created CheckpointRecord.
        """
        return self.create_checkpoint(
            project_state, task_graph,
            checkpoint_type="phase",
            description=f"Phase complete: {project_state.current_phase}",
        )

    def create_milestone_checkpoint(
        self,
        project_state: ProjectState,
        task_graph: TaskGraph,
        milestone_name: str,
    ) -> CheckpointRecord:
        """Create a checkpoint marking a milestone.

        Args:
            project_state: The current project state.
            task_graph: The current task graph.
            milestone_name: The milestone name.

        Returns:
            The created CheckpointRecord.
        """
        return self.create_checkpoint(
            project_state, task_graph,
            checkpoint_type="milestone",
            description=f"Milestone: {milestone_name}",
        )

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    def rollback_to(self, checkpoint_id: str) -> RollbackResult:
        """Rollback project state to a specific checkpoint.

        Args:
            checkpoint_id: The checkpoint to restore to.

        Returns:
            RollbackResult with details of what was rolled back.
        """
        # Load checkpoint
        checkpoint_file = self._checkpoint_dir / f"{checkpoint_id}.json"
        if not checkpoint_file.exists():
            return RollbackResult(
                rollback_id=uuid.uuid4().hex[:12],
                scope="project",
                checkpoint_id=checkpoint_id,
                success=False,
                issues=[f"Checkpoint '{checkpoint_id}' not found"],
            )

        try:
            data = json.loads(checkpoint_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            return RollbackResult(
                rollback_id=uuid.uuid4().hex[:12],
                scope="project",
                checkpoint_id=checkpoint_id,
                success=False,
                issues=[f"Failed to load checkpoint: {exc}"],
            )

        # Restore state file
        state_data = data.get("project_state", {})
        state_file = self._state_dir / "project_state.json"
        state_file.write_text(json.dumps(state_data, indent=2), encoding="utf-8")

        result = RollbackResult(
            rollback_id=uuid.uuid4().hex[:12],
            scope="project",
            target_id=state_data.get("project_id", ""),
            checkpoint_id=checkpoint_id,
            success=True,
            tasks_rolled_back=[],
            tasks_preserved=[],
        )

        self._publish_event("builder.rolled_back", {
            "checkpoint_id": checkpoint_id,
            "project_id": result.target_id,
            "scope": "project",
        })

        logger.info("Rolled back to checkpoint '%s'", checkpoint_id[:8])
        return result

    def rollback_phase(self, phase_name: str) -> RollbackResult:
        """Rollback a specific phase to its initial state.

        Args:
            phase_name: The phase to rollback.

        Returns:
            RollbackResult for the phase rollback.
        """
        # Find the checkpoint just before this phase
        all_checkpoints = self.list_checkpoints()
        target_checkpoint: str | None = None

        for cp in reversed(all_checkpoints):
            if cp.phase != phase_name:
                target_checkpoint = cp.checkpoint_id
                break

        if target_checkpoint:
            result = self.rollback_to(target_checkpoint)
            result.scope = "phase"
            result.target_id = phase_name
            return result

        return RollbackResult(
            rollback_id=uuid.uuid4().hex[:12],
            scope="phase",
            target_id=phase_name,
            success=False,
            issues=[f"No checkpoint found before phase '{phase_name}'"],
        )

    # ------------------------------------------------------------------
    # Checkpoint listing
    # ------------------------------------------------------------------

    def list_checkpoints(self) -> list[CheckpointRecord]:
        """List all available checkpoints in chronological order.

        Returns:
            List of CheckpointRecord objects.
        """
        if not self._checkpoint_dir.exists():
            return []

        checkpoints: list[CheckpointRecord] = []
        for cp_file in sorted(self._checkpoint_dir.glob("*.json"), key=lambda p: p.stat().st_mtime):
            try:
                data = json.loads(cp_file.read_text(encoding="utf-8"))
                checkpoints.append(CheckpointRecord(
                    checkpoint_id=data.get("checkpoint_id", cp_file.stem),
                    timestamp=data.get("timestamp", ""),
                    checkpoint_type=data.get("checkpoint_type", "automatic"),
                    phase=data.get("phase", ""),
                    task_id=data.get("task_id", ""),
                    description=data.get("description", ""),
                ))
            except (json.JSONDecodeError, OSError):
                continue

        return checkpoints

    def get_latest_checkpoint(self) -> CheckpointRecord | None:
        """Get the most recent checkpoint.

        Returns:
            The latest CheckpointRecord, or None.
        """
        checkpoints = self.list_checkpoints()
        return checkpoints[-1] if checkpoints else None

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    def _serialize_project_state(self, state: ProjectState) -> dict[str, Any]:
        """Serialize project state to a dictionary.

        Args:
            state: The project state.

        Returns:
            JSON-compatible dictionary.
        """
        return {
            "project_id": state.project_id,
            "project_name": state.project_name,
            "project_type": state.project_type,
            "status": state.status,
            "current_phase": state.current_phase,
            "phases": {
                name: {
                    "phase": ps.phase,
                    "status": ps.status,
                    "started_at": ps.started_at,
                    "completed_at": ps.completed_at,
                    "completed_tasks": ps.completed_tasks,
                    "failed_tasks": ps.failed_tasks,
                    "artifacts": ps.artifacts,
                }
                for name, ps in state.phases.items()
            },
            "completed_phases": state.completed_phases,
            "failed_phases": state.failed_phases,
            "started_at": state.started_at,
            "updated_at": state.updated_at,
            "completed_at": state.completed_at,
            "metadata": state.metadata,
        }

    def _serialize_task_graph(self, graph: TaskGraph) -> dict[str, Any]:
        """Serialize task graph to a dictionary.

        Args:
            graph: The task graph.

        Returns:
            JSON-compatible dictionary.
        """
        return {
            "graph_id": graph.graph_id,
            "project_id": graph.project_id,
            "nodes": {tid: node.to_dict() for tid, node in graph.nodes.items()},
            "phases": graph.phases,
        }

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(
                type=event_type, data=data, source="rollback_manager",
            ))
        except Exception:
            pass
