"""State Manager — tracks project state, current phase, current task, history, milestones, and statistics.

Maintains the complete project state throughout the builder lifecycle.
Publishes state change events for observability.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.builder.data_models import (
    PhaseState,
    ProjectState,
    TaskGraph,
)
from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class StateManager:
    """Manages the project state throughout the builder lifecycle.

    Tracks:
    - Project state (current phase/task)
    - Phase transitions
    - Task execution history
    - Milestone completion
    - Statistics

    Usage:
        >>> mgr = StateManager(state_dir="/path/to/.builder")
        >>> mgr.initialize(project_state)
        >>> mgr.transition_to("executing")
        >>> print(mgr.current_state.current_phase)
    """

    def __init__(
        self,
        state_dir: str | Path = ".builder",
        event_bus: EventBus | None = None,
    ) -> None:
        """Initialize the State Manager.

        Args:
            state_dir: Directory for state persistence.
            event_bus: Optional EventBus for publishing events.
        """
        self._state_dir = Path(state_dir)
        self._state_file = self._state_dir / "project_state.json"
        self._event_bus = event_bus
        self._current_state: ProjectState | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def current_state(self) -> ProjectState | None:
        """Get the current project state."""
        return self._current_state

    def initialize(self, state: ProjectState) -> None:
        """Initialize state management with a project state.

        Args:
            state: The initial project state.
        """
        self._current_state = state
        self._persist()

    def load(self, project_id: str) -> ProjectState | None:
        """Load project state from disk.

        Args:
            project_id: The project identifier.

        Returns:
            The loaded ProjectState, or None.
        """
        if not self._state_file.exists():
            return None

        try:
            data = json.loads(self._state_file.read_text(encoding="utf-8"))
            if data.get("project_id") != project_id:
                return None

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

            # Restore phases
            for name, ps_data in data.get("phases", {}).items():
                state.phases[name] = PhaseState(
                    phase=ps_data.get("phase", name),
                    status=ps_data.get("status", "pending"),
                    started_at=ps_data.get("started_at", ""),
                    completed_at=ps_data.get("completed_at", ""),
                    completed_tasks=ps_data.get("completed_tasks", []),
                    failed_tasks=ps_data.get("failed_tasks", []),
                    artifacts=ps_data.get("artifacts", []),
                    metadata=ps_data.get("metadata", {}),
                )

            state.completed_phases = data.get("completed_phases", [])
            state.failed_phases = data.get("failed_phases", [])

            self._current_state = state
            return state

        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load state: %s", exc)
            return None

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def transition_to(self, phase_name: str) -> None:
        """Transition the project to a new phase.

        Args:
            phase_name: The target phase.
        """
        if self._current_state is None:
            logger.warning("No current state to transition")
            return

        old_phase = self._current_state.current_phase
        now = datetime.now(timezone.utc).isoformat()

        # Mark old phase as completed
        if old_phase and old_phase in self._current_state.phases:
            old = self._current_state.phases[old_phase]
            old.status = "completed"
            old.completed_at = now
            self._current_state.completed_phases.append(old_phase)

        # Mark new phase as running
        if phase_name in self._current_state.phases:
            new_phase = self._current_state.phases[phase_name]
            new_phase.status = "running"
            new_phase.started_at = new_phase.started_at or now

        self._current_state.current_phase = phase_name
        self._current_state.updated_at = now

        self._persist()
        self._publish_event("builder.phase_transition", {
            "project_id": self._current_state.project_id,
            "from_phase": old_phase,
            "to_phase": phase_name,
        })
        if old_phase and old_phase != phase_name:
            self._publish_event("builder.phase_completed", {
                "project_id": self._current_state.project_id,
                "phase": old_phase,
                "new_phase": phase_name,
            })

        logger.info("Phase transition: '%s' -> '%s'", old_phase, phase_name)

    def update_status(self, status: str) -> None:
        """Update the project status.

        Args:
            status: New status string.
        """
        if self._current_state is None:
            return

        old_status = self._current_state.status
        self._current_state.status = status
        self._current_state.updated_at = datetime.now(timezone.utc).isoformat()

        if status in ("completed", "failed"):
            self._current_state.completed_at = self._current_state.updated_at

        self._persist()
        logger.debug("Status update: '%s' -> '%s'", old_status, status)

    # ------------------------------------------------------------------
    # Task tracking
    # ------------------------------------------------------------------

    def record_completed_task(self, task_id: str, phase: str) -> None:
        """Record a task as completed.

        Args:
            task_id: The completed task ID.
            phase: The phase the task belongs to.
        """
        if self._current_state is None:
            return

        if phase in self._current_state.phases:
            self._current_state.phases[phase].completed_tasks.append(task_id)

        self._current_state.updated_at = datetime.now(timezone.utc).isoformat()
        self._persist()

    def record_failed_task(self, task_id: str, phase: str) -> None:
        """Record a task as failed.

        Args:
            task_id: The failed task ID.
            phase: The phase the task belongs to.
        """
        if self._current_state is None:
            return

        if phase in self._current_state.phases:
            self._current_state.phases[phase].failed_tasks.append(task_id)

        self._current_state.updated_at = datetime.now(timezone.utc).isoformat()
        self._persist()

    def record_artifact(self, artifact_id: str, phase: str) -> None:
        """Record an artifact as produced.

        Args:
            artifact_id: The artifact identifier.
            phase: The phase that produced it.
        """
        if self._current_state is None:
            return

        if phase in self._current_state.phases:
            self._current_state.phases[phase].artifacts.append(artifact_id)

        self._current_state.updated_at = datetime.now(timezone.utc).isoformat()
        self._persist()

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_statistics(self) -> dict[str, Any]:
        """Get project statistics.

        Returns:
            Dict with statistics.
        """
        if self._current_state is None:
            return {}

        total_tasks = sum(
            len(p.completed_tasks) + len(p.failed_tasks)
            for p in self._current_state.phases.values()
        )
        completed_tasks = sum(
            len(p.completed_tasks)
            for p in self._current_state.phases.values()
        )

        return {
            "project_id": self._current_state.project_id,
            "status": self._current_state.status,
            "current_phase": self._current_state.current_phase,
            "completed_phases": len(self._current_state.completed_phases),
            "total_phases": len(self._current_state.phases),
            "completed_tasks": completed_tasks,
            "total_tasks": total_tasks,
            "completion_percentage": round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0.0,
            "started_at": self._current_state.started_at,
            "updated_at": self._current_state.updated_at,
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist(self) -> None:
        """Persist the current state to disk."""
        if self._current_state is None:
            return

        self._state_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "project_id": self._current_state.project_id,
            "project_name": self._current_state.project_name,
            "project_type": self._current_state.project_type,
            "status": self._current_state.status,
            "current_phase": self._current_state.current_phase,
            "phases": {
                name: {
                    "phase": ps.phase,
                    "status": ps.status,
                    "started_at": ps.started_at,
                    "completed_at": ps.completed_at,
                    "completed_tasks": ps.completed_tasks,
                    "failed_tasks": ps.failed_tasks,
                    "artifacts": ps.artifacts,
                    "metadata": ps.metadata,
                }
                for name, ps in self._current_state.phases.items()
            },
            "completed_phases": self._current_state.completed_phases,
            "failed_phases": self._current_state.failed_phases,
            "started_at": self._current_state.started_at,
            "updated_at": self._current_state.updated_at,
            "completed_at": self._current_state.completed_at,
            "metadata": self._current_state.metadata,
        }

        try:
            self._state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("Failed to persist state: %s", exc)

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(
                type=event_type, data=data, source="state_manager",
            ))
        except Exception:
            pass
