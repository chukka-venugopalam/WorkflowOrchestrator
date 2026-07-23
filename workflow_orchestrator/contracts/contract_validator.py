"""Contract validator — validates contract data and lifecycle.

Validates:
- Required fields are present
- Data integrity
- Lifecycle transitions
- Constraint consistency
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.contracts.contract_schema import ContractStatus
from workflow_orchestrator.contracts.project_contract import ProjectContract

logger = logging.getLogger(__name__)


class ContractValidator:
    """Validates project contracts for correctness and completeness.

    Usage:
        >>> validator = ContractValidator()
        >>> result = validator.validate(contract)
        >>> if result["valid"]:
        ...     print("Contract is valid")
    """

    def validate(self, contract: ProjectContract) -> dict[str, Any]:
        """Validate a project contract.

        Args:
            contract: The contract to validate.

        Returns:
            Dict with keys: valid (bool), errors (list), warnings (list).
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Check required fields
        if not contract.project_name:
            errors.append("Project name is required")

        if not contract.version:
            errors.append("Version is required")

        # Validate version format
        if contract.version:
            parts = contract.version.split(".")
            if len(parts) != 3:
                warnings.append(f"Version '{contract.version}' is not semantic (expected X.Y.Z)")
            else:
                for part in parts:
                    if not part.isdigit():
                        warnings.append(f"Version part '{part}' is not numeric")

        # Validate status
        if contract.status not in ContractStatus:
            errors.append(f"Invalid contract status: {contract.status}")

        # Validate data
        data = contract.data

        # Tech stack validation
        if not data.tech_stack.framework and data.tech_stack.language:
            warnings.append("Language set but no framework specified")
        if data.tech_stack.framework and not data.tech_stack.language:
            warnings.append("Framework set but no language specified")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def can_transition(self, contract: ProjectContract, target_status: ContractStatus) -> bool:
        """Check if a status transition is allowed.

        Args:
            contract: The contract to check.
            target_status: The desired target status.

        Returns:
            True if the transition is valid.
        """
        current = contract.status
        allowed: dict[ContractStatus, list[ContractStatus]] = {
            ContractStatus.DRAFT: [ContractStatus.FINALIZED],
            ContractStatus.FINALIZED: [ContractStatus.SUPERSEDED, ContractStatus.ARCHIVED],
            ContractStatus.SUPERSEDED: [ContractStatus.ARCHIVED],
            ContractStatus.ARCHIVED: [],
        }
        return target_status in allowed.get(current, [])
