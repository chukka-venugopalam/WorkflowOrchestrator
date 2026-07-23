"""Context snapshot — persistent snapshots for context reuse and rollback.

Supports:
- Deterministic snapshot creation
- Snapshot-based context reconstruction
- Efficiency: avoid context reassembly for repeated steps
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from workflow_orchestrator.context.context_models import (
    ContextAssembly,
    ContextSnapshot,
)

logger = logging.getLogger(__name__)


class ContextSnapshotManager:
    """Manages context snapshots for reuse and rollback.

    Each snapshot captures the full context at a point in time.
    Snapshots can be used to reconstruct context without reassembly.

    Usage:
        >>> mgr = ContextSnapshotManager()
        >>> snap = mgr.create(assembly, workflow_id="wf-1", step_index=3)
        >>> restored = mgr.load(snap.snapshot_id)
    """

    def __init__(self) -> None:
        self._snapshots: dict[str, ContextSnapshot] = {}

    def create(
        self,
        assembly: ContextAssembly,
        workflow_id: str = "",
        step_index: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> ContextSnapshot:
        """Create a snapshot of the current context.

        Args:
            assembly: The context assembly to snapshot.
            workflow_id: Associated workflow ID.
            step_index: Current step index.
            metadata: Additional metadata.

        Returns:
            The created ContextSnapshot.
        """
        snapshot_id = uuid.uuid4().hex[:12]
        snapshot = ContextSnapshot(
            snapshot_id=snapshot_id,
            assembly=assembly,
            workflow_id=workflow_id,
            step_index=step_index,
            created_at=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )
        self._snapshots[snapshot_id] = snapshot
        logger.debug("Created context snapshot '%s' for workflow '%s'", snapshot_id, workflow_id)
        return snapshot

    def load(self, snapshot_id: str) -> ContextSnapshot | None:
        """Load a snapshot by ID.

        Args:
            snapshot_id: The snapshot identifier.

        Returns:
            The ContextSnapshot, or None if not found.
        """
        return self._snapshots.get(snapshot_id)

    def load_assembly(self, snapshot_id: str) -> ContextAssembly | None:
        """Load only the assembly from a snapshot.

        Args:
            snapshot_id: The snapshot identifier.

        Returns:
            The ContextAssembly, or None if not found.
        """
        snapshot = self.load(snapshot_id)
        return snapshot.assembly if snapshot else None

    def find_by_workflow(self, workflow_id: str) -> list[ContextSnapshot]:
        """Find all snapshots for a workflow.

        Args:
            workflow_id: The workflow identifier.

        Returns:
            List of snapshots, newest first.
        """
        results = [s for s in self._snapshots.values() if s.workflow_id == workflow_id]
        return sorted(results, key=lambda s: s.created_at, reverse=True)

    def find_by_step(self, workflow_id: str, step_index: int) -> ContextSnapshot | None:
        """Find the snapshot for a specific step in a workflow.

        Args:
            workflow_id: The workflow identifier.
            step_index: The step index.

        Returns:
            The matching snapshot, or None.
        """
        for snapshot in self._snapshots.values():
            if snapshot.workflow_id == workflow_id and snapshot.step_index == step_index:
                return snapshot
        return None

    def remove(self, snapshot_id: str) -> bool:
        """Remove a snapshot.

        Args:
            snapshot_id: The snapshot to remove.

        Returns:
            True if removed, False if not found.
        """
        return self._snapshots.pop(snapshot_id, None) is not None

    def clear(self) -> None:
        """Clear all snapshots."""
        self._snapshots.clear()

    @property
    def count(self) -> int:
        """Number of stored snapshots."""
        return len(self._snapshots)
