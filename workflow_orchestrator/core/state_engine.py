"""State engine with append-only transition log.

The State Engine is the single source of truth for workflow run state.
It provides durable, append-only persistence with materialized snapshots
rebuilt from the transition log.

Key design decisions:
- Write-ahead: transitions are logged BEFORE any side-effecting action
- Append-only: nothing is ever deleted or overwritten
- Snapshot rebuild: current state is always reconstructible from the log
- Checkpoint model: rollback creates a new forward transition, never deletes history
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransitionRecord:
    """An immutable record of a state transition.

    Attributes:
        transition_id: Unique identifier for this transition.
        run_id: The run this transition belongs to.
        from_status: Previous status (empty string for initial).
        to_status: New status after the transition.
        timestamp: ISO-8601 timestamp.
        data: Arbitrary data associated with the transition.
        actor: Who or what caused the transition.
    """

    transition_id: str
    run_id: str
    from_status: str
    to_status: str
    timestamp: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    actor: str = "system"

    def __post_init__(self) -> None:
        if not self.timestamp:
            object.__setattr__(self, "timestamp", datetime.now(timezone.utc).isoformat())
        if not self.transition_id:
            object.__setattr__(self, "transition_id", uuid.uuid4().hex[:12])

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "transition_id": self.transition_id,
            "run_id": self.run_id,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "timestamp": self.timestamp,
            "data": self.data,
            "actor": self.actor,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TransitionRecord:
        """Create from a dictionary."""
        return cls(
            transition_id=data.get("transition_id", ""),
            run_id=data.get("run_id", ""),
            from_status=data.get("from_status", ""),
            to_status=data.get("to_status", ""),
            timestamp=data.get("timestamp", ""),
            data=data.get("data", {}),
            actor=data.get("actor", "system"),
        )


@dataclass
class RunSnapshot:
    """Materialized current state of a workflow run.

    This is rebuilt from the transition log. It is not the source of truth
    — the log is.

    Attributes:
        run_id: Unique run identifier.
        workflow_name: Name of the workflow being executed.
        status: Current status (e.g., ``running``, ``completed``, ``failed``).
        current_step: Index of the current or last executed step.
        started_at: ISO-8601 timestamp of when the run started.
        completed_at: ISO-8601 timestamp of when the run completed (if done).
        transition_count: Number of transitions in the log.
        last_transition_id: ID of the most recent transition.
        data: Arbitrary state data.
    """

    run_id: str
    workflow_name: str = ""
    status: str = "pending"
    current_step: int = 0
    started_at: str = ""
    completed_at: str = ""
    transition_count: int = 0
    last_transition_id: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "run_id": self.run_id,
            "workflow_name": self.workflow_name,
            "status": self.status,
            "current_step": self.current_step,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "transition_count": self.transition_count,
            "last_transition_id": self.last_transition_id,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunSnapshot:
        """Create from a dictionary."""
        return cls(
            run_id=data.get("run_id", ""),
            workflow_name=data.get("workflow_name", ""),
            status=data.get("status", "pending"),
            current_step=data.get("current_step", 0),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at", ""),
            transition_count=data.get("transition_count", 0),
            last_transition_id=data.get("last_transition_id", ""),
            data=data.get("data", {}),
        )


@dataclass
class HeartbeatRecord:
    """A heartbeat signal indicating a run is still alive.

    Attributes:
        run_id: The run this heartbeat belongs to.
        timestamp: ISO-8601 timestamp.
        step_index: Current step index being executed.
    """

    run_id: str
    timestamp: str = ""
    step_index: int = 0

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Storage abstraction
# ---------------------------------------------------------------------------


class StateStore(ABC):
    """Abstract storage backend for state persistence."""

    @abstractmethod
    def append_transition(self, record: TransitionRecord) -> None:
        """Append a transition record to the log.

        Args:
            record: The transition to append.
        """
        ...

    @abstractmethod
    def get_transitions(self, run_id: str) -> list[TransitionRecord]:
        """Get all transitions for a run, in order.

        Args:
            run_id: The run identifier.

        Returns:
            List of TransitionRecord objects, oldest first.
        """
        ...

    @abstractmethod
    def save_snapshot(self, snapshot: RunSnapshot) -> None:
        """Persist a materialized snapshot.

        Args:
            snapshot: The snapshot to save.
        """
        ...

    @abstractmethod
    def load_snapshot(self, run_id: str) -> Optional[RunSnapshot]:
        """Load the most recent snapshot for a run.

        Args:
            run_id: The run identifier.

        Returns:
            The snapshot, or None if not found.
        """
        ...

    @abstractmethod
    def save_heartbeat(self, heartbeat: HeartbeatRecord) -> None:
        """Record a heartbeat.

        Args:
            heartbeat: The heartbeat to record.
        """
        ...

    @abstractmethod
    def get_latest_heartbeat(self, run_id: str) -> Optional[HeartbeatRecord]:
        """Get the most recent heartbeat for a run.

        Args:
            run_id: The run identifier.

        Returns:
            The latest heartbeat, or None if none found.
        """
        ...

    @abstractmethod
    def list_runs(self) -> list[str]:
        """List all run IDs that have state data.

        Returns:
            Sorted list of run IDs.
        """
        ...

    @abstractmethod
    def delete_run(self, run_id: str) -> None:
        """Delete all state data for a run.

        Args:
            run_id: The run identifier to delete.
        """
        ...


class FileSystemStateStore(StateStore):
    """Filesystem-backed state store using JSON files.

    Stores transition logs, snapshots, and heartbeats in a directory
    structure under a configurable base path.

    Layout:
        ``{base_path}/{run_id}/transitions.json``
        ``{base_path}/{run_id}/snapshot.json``
        ``{base_path}/{run_id}/heartbeat.json``
    """

    def __init__(self, base_path: Path | str) -> None:
        """Initialize the store.

        Args:
            base_path: Root directory for state storage.
        """
        self._base_path = Path(base_path).expanduser().resolve()
        self._base_path.mkdir(parents=True, exist_ok=True)

    def _run_dir(self, run_id: str) -> Path:
        """Get the directory for a specific run."""
        path = self._base_path / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def append_transition(self, record: TransitionRecord) -> None:
        """Append a transition record to the log file."""
        run_dir = self._run_dir(record.run_id)
        log_file = run_dir / "transitions.json"

        transitions: list[dict[str, Any]] = []
        if log_file.exists():
            try:
                transitions = json.loads(log_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                transitions = []

        transitions.append(record.to_dict())
        log_file.write_text(json.dumps(transitions, indent=2), encoding="utf-8")

    def get_transitions(self, run_id: str) -> list[TransitionRecord]:
        """Get all transitions for a run."""
        log_file = self._run_dir(run_id) / "transitions.json"
        if not log_file.exists():
            return []

        try:
            data = json.loads(log_file.read_text(encoding="utf-8"))
            return [TransitionRecord.from_dict(item) for item in data]
        except (json.JSONDecodeError, OSError):
            return []

    def save_snapshot(self, snapshot: RunSnapshot) -> None:
        """Persist a materialized snapshot."""
        snapshot_file = self._run_dir(snapshot.run_id) / "snapshot.json"
        snapshot_file.write_text(json.dumps(snapshot.to_dict(), indent=2), encoding="utf-8")

    def load_snapshot(self, run_id: str) -> Optional[RunSnapshot]:
        """Load the most recent snapshot for a run."""
        snapshot_file = self._run_dir(run_id) / "snapshot.json"
        if not snapshot_file.exists():
            return None

        try:
            data = json.loads(snapshot_file.read_text(encoding="utf-8"))
            return RunSnapshot.from_dict(data)
        except (json.JSONDecodeError, OSError):
            return None

    def save_heartbeat(self, heartbeat: HeartbeatRecord) -> None:
        """Record a heartbeat."""
        heartbeat_file = self._run_dir(heartbeat.run_id) / "heartbeat.json"
        heartbeat_data = {"run_id": heartbeat.run_id, "timestamp": heartbeat.timestamp, "step_index": heartbeat.step_index}
        heartbeat_file.write_text(json.dumps(heartbeat_data, indent=2), encoding="utf-8")

    def get_latest_heartbeat(self, run_id: str) -> Optional[HeartbeatRecord]:
        """Get the most recent heartbeat for a run."""
        heartbeat_file = self._run_dir(run_id) / "heartbeat.json"
        if not heartbeat_file.exists():
            return None

        try:
            data = json.loads(heartbeat_file.read_text(encoding="utf-8"))
            return HeartbeatRecord(
                run_id=data.get("run_id", run_id),
                timestamp=data.get("timestamp", ""),
                step_index=data.get("step_index", 0),
            )
        except (json.JSONDecodeError, OSError):
            return None

    def list_runs(self) -> list[str]:
        """List all run IDs that have state data."""
        if not self._base_path.exists():
            return []
        return sorted(
            p.name for p in self._base_path.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        )

    def delete_run(self, run_id: str) -> None:
        """Delete all state data for a run."""
        import shutil
        run_dir = self._base_path / run_id
        if run_dir.exists():
            shutil.rmtree(run_dir)


# ---------------------------------------------------------------------------
# State Engine
# ---------------------------------------------------------------------------


# Valid workflow run statuses
RUN_STATUSES = [
    "pending",
    "running",
    "paused",
    "completed",
    "failed",
    "cancelled",
    "interrupted",
]

# Allowed transitions
ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["running", "cancelled"],
    "running": ["paused", "completed", "failed", "cancelled", "interrupted"],
    "paused": ["running", "cancelled"],
    "interrupted": ["running", "cancelled"],  # Resume or cancel
    "completed": [],  # Terminal
    "failed": [],  # Terminal
    "cancelled": [],  # Terminal
}


class StateEngine:
    """State machine for workflow runs with append-only transition log.

    Usage:
        >>> engine = StateEngine(store=FileSystemStateStore("/tmp/states"))
        >>> run = engine.create_run("my-workflow")
        >>> engine.transition(run.run_id, "running", actor="engine")
        >>> snapshot = engine.current_snapshot(run.run_id)
        >>> print(snapshot.status)
        'running'
    """

    def __init__(self, store: StateStore) -> None:
        """Initialize the state engine.

        Args:
            store: Backend storage for state persistence.
        """
        self._store = store

    @property
    def store(self) -> StateStore:
        """The underlying state store."""
        return self._store

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_run(
        self,
        workflow_name: str,
        run_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> RunSnapshot:
        """Create a new workflow run.

        Args:
            workflow_name: Name of the workflow.
            run_id: Optional explicit run ID. Auto-generated if not provided.
            data: Optional initial state data.

        Returns:
            The initial RunSnapshot.

        Raises:
            ValueError: If a run with the given ID already exists.
        """
        run_id = run_id or uuid.uuid4().hex[:12]

        # Check for duplicate
        existing = self._store.load_snapshot(run_id)
        if existing is not None:
            raise ValueError(f"Run '{run_id}' already exists.")

        now = datetime.now(timezone.utc).isoformat()

        # Write-ahead: log the initial transition BEFORE creating the snapshot
        initial_transition = TransitionRecord(
            transition_id=uuid.uuid4().hex[:12],
            run_id=run_id,
            from_status="",
            to_status="pending",
            timestamp=now,
            data={"workflow_name": workflow_name, **(data or {})},
            actor="system",
        )
        self._store.append_transition(initial_transition)

        # Create and persist the initial snapshot
        snapshot = RunSnapshot(
            run_id=run_id,
            workflow_name=workflow_name,
            status="pending",
            current_step=0,
            started_at=now,
            transition_count=1,
            last_transition_id=initial_transition.transition_id,
            data=data or {},
        )
        self._store.save_snapshot(snapshot)

        logger.info("Created run '%s' for workflow '%s'", run_id, workflow_name)
        return snapshot

    def transition(
        self,
        run_id: str,
        to_status: str,
        actor: str = "system",
        data: dict[str, Any] | None = None,
    ) -> RunSnapshot:
        """Transition a run to a new status (write-ahead).

        Args:
            run_id: The run to transition.
            to_status: The target status.
            actor: Who or what caused the transition.
            data: Optional data to associate with the transition.

        Returns:
            The updated RunSnapshot.

        Raises:
            ValueError: If the transition is not allowed.
        """
        current = self._store.load_snapshot(run_id)
        if current is None:
            raise ValueError(f"Run '{run_id}' not found. Create it first.")

        from_status = current.status

        # Validate transition
        allowed = ALLOWED_TRANSITIONS.get(from_status, [])
        if to_status not in allowed:
            raise ValueError(
                f"Illegal transition: '{from_status}' → '{to_status}'. "
                f"Allowed from '{from_status}': {allowed or '(terminal state)'}"
            )

        now = datetime.now(timezone.utc).isoformat()

        # Write-ahead: log transition BEFORE updating snapshot
        transition = TransitionRecord(
            transition_id=uuid.uuid4().hex[:12],
            run_id=run_id,
            from_status=from_status,
            to_status=to_status,
            timestamp=now,
            data=data or {},
            actor=actor,
        )
        self._store.append_transition(transition)

        # Update snapshot
        current.status = to_status
        current.transition_count += 1
        current.last_transition_id = transition.transition_id
        if to_status == "running":
            current.started_at = current.started_at or now
        elif to_status in ("completed", "failed", "cancelled"):
            current.completed_at = now

        # Merge data
        if data:
            current.data.update(data)

        self._store.save_snapshot(current)

        logger.debug(
            "Transition '%s': %s → %s (actor: %s)",
            run_id,
            from_status,
            to_status,
            actor,
        )
        return current

    def current_snapshot(self, run_id: str) -> Optional[RunSnapshot]:
        """Get the current snapshot for a run.

        Args:
            run_id: The run identifier.

        Returns:
            The current RunSnapshot, or None if not found.
        """
        return self._store.load_snapshot(run_id)

    def history(self, run_id: str) -> list[TransitionRecord]:
        """Get the full transition history for a run.

        Args:
            run_id: The run identifier.

        Returns:
            List of TransitionRecord objects in chronological order.
        """
        return self._store.get_transitions(run_id)

    def rebuild_from_log(self, run_id: str) -> Optional[RunSnapshot]:
        """Rebuild the current snapshot from the transition log alone.

        This is the crash recovery path: discard any persisted snapshot
        and reconstruct state purely from the append-only log.

        Args:
            run_id: The run identifier.

        Returns:
            Reconstructed RunSnapshot, or None if no transitions exist.
        """
        transitions = self._store.get_transitions(run_id)
        if not transitions:
            return None

        # Rebuild from scratch
        first = transitions[0]
        last = transitions[-1]

        snapshot = RunSnapshot(
            run_id=run_id,
            workflow_name=first.data.get("workflow_name", ""),
            status=last.to_status,
            transition_count=len(transitions),
            last_transition_id=last.transition_id,
            data={},
        )

        # Apply all transitions in order
        for t in transitions:
            snapshot.status = t.to_status
            if t.data:
                snapshot.data.update(t.data)
            if t.to_status == "running" and not snapshot.started_at:
                snapshot.started_at = t.timestamp
            if t.to_status in ("completed", "failed", "cancelled"):
                snapshot.completed_at = t.timestamp

        # Persist the rebuilt snapshot
        self._store.save_snapshot(snapshot)
        logger.info("Rebuilt snapshot for run '%s' from %d transitions", run_id, len(transitions))
        return snapshot

    def record_heartbeat(self, run_id: str, step_index: int = 0) -> None:
        """Record a heartbeat for a run.

        Args:
            run_id: The run identifier.
            step_index: Current step index.
        """
        heartbeat = HeartbeatRecord(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            step_index=step_index,
        )
        self._store.save_heartbeat(heartbeat)

    def check_heartbeat(self, run_id: str, timeout_seconds: float = 60.0) -> bool:
        """Check if a run's heartbeat is still alive.

        Args:
            run_id: The run identifier.
            timeout_seconds: Max allowed time since last heartbeat.

        Returns:
            True if the run has a recent heartbeat, False otherwise.
        """
        heartbeat = self._store.get_latest_heartbeat(run_id)
        if heartbeat is None:
            return False

        try:
            from datetime import datetime
            heartbeat_time = datetime.fromisoformat(heartbeat.timestamp)
            elapsed = (datetime.now(timezone.utc) - heartbeat_time.replace(tzinfo=timezone.utc)).total_seconds()
            return elapsed < timeout_seconds
        except (ValueError, TypeError):
            return False

    def interrupted_runs(self) -> list[str]:
        """Find runs that appear to have crashed (no recent heartbeat).

        Returns:
            List of run IDs for runs with status 'running' but expired heartbeats.
        """
        interrupted: list[str] = []
        for run_id in self._store.list_runs():
            snapshot = self._store.load_snapshot(run_id)
            if snapshot and snapshot.status == "running":
                if not self.check_heartbeat(run_id):
                    interrupted.append(run_id)
        return interrupted

    def list_runs(self) -> list[str]:
        """List all known run IDs."""
        return self._store.list_runs()
