"""Contract snapshot — snapshots of contract state at version points."""

from __future__ import annotations

import json
import logging
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Optional

from workflow_orchestrator.contracts.project_contract import ProjectContract

logger = logging.getLogger(__name__)


class ContractSnapshot:
    """A frozen snapshot of a contract at a point in time."""

    def __init__(self, contract: ProjectContract) -> None:
        self.snapshot_id: str = uuid.uuid4().hex[:12]
        self.contract_id: str = contract.contract_id
        self.version: str = contract.version
        self.status: str = contract.status.value
        self.project_name: str = contract.project_name
        self.data: dict[str, Any] = self._serialize_data(contract)
        self.created_at: str = datetime.now(timezone.utc).isoformat()

    def _serialize_data(self, contract: ProjectContract) -> dict[str, Any]:
        return {
            "vision": contract.data.vision,
            "requirements": list(contract.data.requirements),
            "architecture": contract.data.architecture,
            "tech_stack": {
                "framework": contract.data.tech_stack.framework,
                "language": contract.data.tech_stack.language,
                "deployment": contract.data.tech_stack.deployment,
            },
            "constraints": [{"category": c.category, "description": c.description, "severity": c.severity}
                           for c in contract.data.constraints],
            "acceptance_criteria": [{"id": c.id, "description": c.description, "category": c.category}
                                    for c in contract.data.acceptance_criteria],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "contract_id": self.contract_id,
            "version": self.version,
            "status": self.status,
            "project_name": self.project_name,
            "data": self.data,
            "created_at": self.created_at,
        }


class ContractSnapshotManager:
    """Manages contract snapshots.

    Usage:
        >>> mgr = ContractSnapshotManager()
        >>> snap = mgr.create(contract)
        >>> snapshot = mgr.load(snap.snapshot_id)
    """

    def __init__(self) -> None:
        self._snapshots: dict[str, ContractSnapshot] = {}

    def create(self, contract: ProjectContract) -> ContractSnapshot:
        """Create a snapshot of a contract.

        Args:
            contract: The contract to snapshot.

        Returns:
            A ContractSnapshot.
        """
        snapshot = ContractSnapshot(contract)
        self._snapshots[snapshot.snapshot_id] = snapshot
        return snapshot

    def load(self, snapshot_id: str) -> ContractSnapshot | None:
        """Load a snapshot by ID.

        Args:
            snapshot_id: The snapshot identifier.

        Returns:
            The ContractSnapshot, or None.
        """
        return self._snapshots.get(snapshot_id)

    def find_by_contract(self, contract_id: str) -> list[ContractSnapshot]:
        """Find all snapshots for a contract.

        Args:
            contract_id: The contract identifier.

        Returns:
            List of snapshots.
        """
        return [s for s in self._snapshots.values() if s.contract_id == contract_id]
