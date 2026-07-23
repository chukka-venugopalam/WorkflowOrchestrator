"""Project Contract — immutable project specification.

Stores:
- Vision / Requirements / Architecture
- Folder Structure / Coding Standards
- Tech Stack / Constraints
- Milestones / Acceptance Criteria
- Human Decisions / Version History

Contracts are immutable per version. Changes produce @vN+1.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from workflow_orchestrator.contracts.contract_schema import (
    AcceptanceCriterion,
    Constraint,
    ContractData,
    ContractMilestone,
    ContractStatus,
    HumanDecision,
    StyleConvention,
    TechStack,
)

logger = logging.getLogger(__name__)


@dataclass
class ProjectContract:
    """An immutable versioned project contract.

    Attributes:
        contract_id: Unique contract identifier.
        version: Semantic version string (e.g., "1.0.0").
        status: Current lifecycle status.
        project_name: Name of the project.
        data: The core contract data.
        parent_version: Previous version ID (empty for v1).
        changelog: Summary of changes from previous version.
        created_at: ISO-8601 creation timestamp.
        finalized_at: ISO-8601 finalization timestamp.
        finalized_by: Who finalized this contract.
        metadata: Additional metadata.
    """

    contract_id: str = ""
    version: str = "1.0.0"
    status: ContractStatus = ContractStatus.DRAFT
    project_name: str = ""
    data: ContractData = field(default_factory=ContractData)
    parent_version: str = ""
    changelog: str = ""
    created_at: str = ""
    finalized_at: str = ""
    finalized_by: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        project_name: str = "",
        version: str = "1.0.0",
        data: ContractData | None = None,
    ) -> ProjectContract:
        """Create a new draft contract.

        Args:
            project_name: Name of the project.
            version: Semantic version string.
            data: Initial contract data.

        Returns:
            A new ProjectContract in DRAFT status.
        """
        return cls(
            contract_id=uuid.uuid4().hex[:12],
            version=version,
            status=ContractStatus.DRAFT,
            project_name=project_name,
            data=data or ContractData(),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def finalize(self, finalized_by: str = "system") -> None:
        """Finalize this contract.

        Once finalized, the contract is immutable.
        Changes must produce a new version.

        Args:
            finalized_by: Who or what finalized this contract.

        Raises:
            ValueError: If the contract is already in a terminal state.
        """
        if self.status in (ContractStatus.FINALIZED, ContractStatus.SUPERSEDED, ContractStatus.ARCHIVED):
            raise ValueError(f"Cannot finalize contract in status '{self.status.value}'")

        self.status = ContractStatus.FINALIZED
        self.finalized_at = datetime.now(timezone.utc).isoformat()
        self.finalized_by = finalized_by
        logger.info("Finalized contract '%s' v%s", self.project_name, self.version)

    def supersede(self) -> None:
        """Mark this contract as superseded (by a newer version)."""
        if self.status == ContractStatus.FINALIZED:
            self.status = ContractStatus.SUPERSEDED
            logger.info("Superseded contract '%s' v%s", self.project_name, self.version)
        else:
            raise ValueError(f"Cannot supersede contract in status '{self.status.value}'")

    def to_summary(self) -> str:
        """Generate a human-readable summary of the contract.

        Returns:
            A formatted string with key contract information.
        """
        lines = [
            f"Project: {self.project_name}",
            f"Version: {self.version} [{self.status.value}]",
            f"Vision: {self.data.vision[:200] if self.data.vision else 'Not defined'}",
        ]

        if self.data.tech_stack.framework:
            lines.append(f"Framework: {self.data.tech_stack.framework}")

        if self.data.tech_stack.language:
            lines.append(f"Language: {self.data.tech_stack.language}")

        if self.data.requirements:
            lines.append(f"Requirements: {len(self.data.requirements)} defined")

        if self.data.constraints:
            lines.append(f"Constraints: {len(self.data.constraints)}")

        if self.data.acceptance_criteria:
            lines.append(f"Acceptance Criteria: {len(self.data.acceptance_criteria)}")

        if self.data.milestones:
            lines.append(f"Milestones: {len(self.data.milestones)}")

        return "\n".join(lines)
