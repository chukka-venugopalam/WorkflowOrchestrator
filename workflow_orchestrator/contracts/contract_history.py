"""Contract history — immutable version history tracking.

Records:
- Contract creation
- Finalization events
- Version bumps
- Human decisions
- Changelog entries
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from workflow_orchestrator.contracts.project_contract import ProjectContract

logger = logging.getLogger(__name__)


@dataclass
class HistoryEntry:
    """A single entry in the contract history.

    Attributes:
        entry_type: Type of event (creation, finalization, version, decision).
        contract_id: ID of the affected contract.
        version: Version at the time of the event.
        description: Human-readable description.
        timestamp: ISO-8601 timestamp.
        actor: Who triggered the event.
        metadata: Additional data.
    """

    entry_type: str
    contract_id: str
    version: str = ""
    description: str = ""
    timestamp: str = ""
    actor: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ContractHistory:
    """Tracks the immutable history of contract changes.

    Usage:
        >>> history = ContractHistory()
        >>> history.record_creation(contract)
        >>> history.record_finalization(contract, "user")
        >>> entries = history.get_history(contract.contract_id)
    """

    def __init__(self) -> None:
        self._entries: list[HistoryEntry] = []

    def record_creation(self, contract: ProjectContract, actor: str = "system") -> None:
        """Record contract creation.

        Args:
            contract: The created contract.
            actor: Who created it.
        """
        self._entries.append(HistoryEntry(
            entry_type="creation",
            contract_id=contract.contract_id,
            version=contract.version,
            description=f"Contract created for '{contract.project_name}'",
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor=actor,
        ))

    def record_finalization(self, contract: ProjectContract, actor: str = "system") -> None:
        """Record contract finalization.

        Args:
            contract: The finalized contract.
            actor: Who finalized it.
        """
        self._entries.append(HistoryEntry(
            entry_type="finalization",
            contract_id=contract.contract_id,
            version=contract.version,
            description=f"Contract '{contract.project_name}' v{contract.version} finalized",
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor=actor,
        ))

    def record_version(self, old: ProjectContract, new: ProjectContract, changelog: str = "") -> None:
        """Record a version bump.

        Args:
            old: The previous version.
            new: The new version.
            changelog: Summary of changes.
        """
        self._entries.append(HistoryEntry(
            entry_type="version",
            contract_id=new.contract_id,
            version=new.version,
            description=f"Version bump: v{old.version} → v{new.version}. {changelog}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "old_version": old.version,
                "new_version": new.version,
                "old_contract_id": old.contract_id,
            },
        ))

    def record_decision(
        self,
        contract: ProjectContract,
        decision: str,
        actor: str = "system",
    ) -> None:
        """Record a human decision.

        Args:
            contract: The affected contract.
            decision: The decision description.
            actor: Who made the decision.
        """
        self._entries.append(HistoryEntry(
            entry_type="decision",
            contract_id=contract.contract_id,
            version=contract.version,
            description=decision,
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor=actor,
        ))

    def get_history(self, contract_id: str) -> list[HistoryEntry]:
        """Get all history entries for a contract.

        Args:
            contract_id: The contract identifier.

        Returns:
            List of history entries, newest first.
        """
        entries = [e for e in self._entries if e.contract_id == contract_id]
        return sorted(entries, key=lambda e: e.timestamp, reverse=True)

    def get_all(self) -> list[HistoryEntry]:
        """Get all history entries.

        Returns:
            List of all entries, newest first.
        """
        return sorted(self._entries, key=lambda e: e.timestamp, reverse=True)
