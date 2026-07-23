"""Contract manager — manages the full contract lifecycle.

Lifecycle: Draft → Finalized → Superseded (→ Archived)

Supports:
- Version management
- Contract creation from templates
- Human approval checkpoints
- Contract summary generation
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from workflow_orchestrator.contracts.contract_schema import (
    AcceptanceCriterion,
    Constraint,
    ContractData,
    ContractStatus,
    HumanDecision,
    StyleConvention,
    TechStack,
)
from workflow_orchestrator.contracts.contract_history import ContractHistory
from workflow_orchestrator.contracts.contract_diff import ContractDiffer
from workflow_orchestrator.contracts.contract_validator import ContractValidator
from workflow_orchestrator.contracts.contract_rules import ContractRules
from workflow_orchestrator.contracts.contract_snapshot import ContractSnapshotManager
from workflow_orchestrator.contracts.project_contract import ProjectContract

logger = logging.getLogger(__name__)


class ContractManager:
    """Manages the full lifecycle of project contracts.

    Usage:
        >>> mgr = ContractManager()
        >>> contract = mgr.create("My Project")
        >>> contract.data.vision = "Build a great product"
        >>> mgr.finalize(contract, finalized_by="user")
        >>> v2 = mgr.create_next_version(contract)
    """

    def __init__(
        self,
        validator: ContractValidator | None = None,
        differ: ContractDiffer | None = None,
        history: ContractHistory | None = None,
        rules: ContractRules | None = None,
        snapshot_manager: ContractSnapshotManager | None = None,
    ) -> None:
        self._validator = validator or ContractValidator()
        self._differ = differ or ContractDiffer()
        self._history = history or ContractHistory()
        self._rules = rules or ContractRules()
        self._snapshot_manager = snapshot_manager or ContractSnapshotManager()

    @property
    def validator(self) -> ContractValidator:
        """The contract validator."""
        return self._validator

    @property
    def history(self) -> ContractHistory:
        """The contract history."""
        return self._history

    @property
    def differ(self) -> ContractDiffer:
        """The contract differ."""
        return self._differ

    def create(self, project_name: str, data: ContractData | None = None) -> ProjectContract:
        """Create a new draft contract.

        Args:
            project_name: Name of the project.
            data: Initial contract data.

        Returns:
            A new draft ProjectContract.
        """
        contract = ProjectContract.create(project_name=project_name, data=data)
        self._history.record_creation(contract)
        logger.info("Created contract for '%s' (v%s)", project_name, contract.version)
        return contract

    def finalize(self, contract: ProjectContract, finalized_by: str = "system") -> ProjectContract:
        """Finalize a contract with human approval checkpoint.

        Args:
            contract: The contract to finalize.
            finalized_by: Who authorized the finalization.

        Returns:
            The finalized contract.

        Raises:
            ValueError: If validation fails or contract is already finalized.
        """
        # Validate before finalization
        validation = self._validator.validate(contract)
        if not validation.get("valid", False):
            errors = validation.get("errors", [])
            raise ValueError(f"Contract validation failed: {'; '.join(errors)}")

        # Check rules
        rule_check = self._rules.check_finalization(contract)
        if not rule_check.get("allowed", False):
            raise ValueError(f"Contract finalization rejected: {rule_check.get('reason', '')}")

        contract.finalize(finalized_by=finalized_by)
        self._history.record_finalization(contract, finalized_by)
        self._snapshot_manager.create(contract)
        logger.info("Finalized contract '%s' v%s by '%s'", contract.project_name, contract.version, finalized_by)
        return contract

    def create_next_version(
        self,
        current: ProjectContract,
        new_data: ContractData | None = None,
        changelog: str = "",
    ) -> ProjectContract:
        """Create the next version of a contract.

        Args:
            current: The current contract to base the new version on.
            new_data: Updated contract data (None = copy current).
            changelog: Description of changes.

        Returns:
            A new draft ProjectContract with incremented version.
        """
        if current.status == ContractStatus.DRAFT:
            raise ValueError("Cannot version a draft contract. Finalize it first.")

        current_version = self._parse_version(current.version)
        new_version = f"{current_version[0] + 1}.0.0"

        data = new_data or ContractData(
            vision=current.data.vision,
            requirements=list(current.data.requirements),
            architecture=current.data.architecture,
            folder_structure=current.data.folder_structure,
            coding_standards=current.data.coding_standards,
            tech_stack=current.data.tech_stack,
            constraints=list(current.data.constraints),
            milestones=list(current.data.milestones),
            acceptance_criteria=list(current.data.acceptance_criteria),
            style_conventions=list(current.data.style_conventions),
            human_decisions=list(current.data.human_decisions),
        )

        new_contract = ProjectContract(
            contract_id=uuid.uuid4().hex[:12],
            version=new_version,
            status=ContractStatus.DRAFT,
            project_name=current.project_name,
            data=data,
            parent_version=current.version,
            changelog=changelog,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Supersede the current version
        current.supersede()
        self._history.record_version(current, new_contract, changelog)
        logger.info("Created v%s from v%s for '%s'", new_version, current.version, current.project_name)
        return new_contract

    def needs_approval(self, contract: ProjectContract) -> bool:
        """Check if this contract requires human approval.

        Approval is required when:
        - Finalizing from DRAFT to FINALIZED
        - Creating a new version that changes constraints

        Args:
            contract: The contract to check.

        Returns:
            True if human approval is required.
        """
        if contract.status == ContractStatus.DRAFT:
            return True
        if contract.status == ContractStatus.FINALIZED:
            return True  # Creating next version needs approval
        return False

    def _parse_version(self, version: str) -> tuple[int, int, int]:
        """Parse a semantic version string.

        Args:
            version: Version string (e.g., "1.2.3").

        Returns:
            Tuple of (major, minor, patch).
        """
        parts = version.split(".")
        major = int(parts[0]) if len(parts) > 0 else 1
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return (major, minor, patch)
