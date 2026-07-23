"""Contract rules — rules for contract lifecycle decisions.

Evaluates whether contracts can be:
- Finalized (human approval required)
- Versioned (changes allowed)
- Archived (no pending work)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.contracts.contract_schema import ContractStatus
from workflow_orchestrator.contracts.project_contract import ProjectContract

logger = logging.getLogger(__name__)


class ContractRules:
    """Evaluates contract lifecycle rules.

    Usage:
        >>> rules = ContractRules()
        >>> result = rules.check_finalization(contract)
        >>> if result["allowed"]:
        ...     contract.finalize()
    """

    def check_finalization(self, contract: ProjectContract) -> dict[str, Any]:
        """Check if a contract can be finalized.

        Rules:
        1. Must have a project name
        2. Must have a vision statement
        3. Must have at least one requirement
        4. Must declare tech stack
        5. Must have at least one acceptance criterion

        Args:
            contract: The contract to check.

        Returns:
            Dict with keys: allowed (bool), reason (str), checks (list).
        """
        checks: list[dict[str, Any]] = []
        all_pass = True

        # Rule 1: Project name
        has_name = bool(contract.project_name)
        checks.append({"rule": "project_name", "pass": has_name, "message": "Project name is required"})
        if not has_name:
            all_pass = False

        # Rule 2: Vision
        has_vision = bool(contract.data.vision)
        checks.append({"rule": "vision", "pass": has_vision, "message": "Vision is required"})
        if not has_vision:
            all_pass = False

        # Rule 3: Requirements
        has_requirements = len(contract.data.requirements) > 0
        checks.append({"rule": "requirements", "pass": has_requirements, "message": "At least one requirement is needed"})
        if not has_requirements:
            all_pass = False

        # Rule 4: Tech stack
        has_tech_stack = bool(contract.data.tech_stack.framework) or bool(contract.data.tech_stack.language)
        checks.append({"rule": "tech_stack", "pass": has_tech_stack, "message": "Tech stack must declare framework or language"})

        # Rule 5: Acceptance criteria
        has_criteria = len(contract.data.acceptance_criteria) > 0
        checks.append({"rule": "acceptance_criteria", "pass": has_criteria, "message": "At least one acceptance criterion is needed"})

        reason = ""
        if not all_pass:
            failed = [c["message"] for c in checks if not c["pass"]]
            reason = f"Finalization blocked: {'; '.join(failed)}"

        return {
            "allowed": all_pass,
            "reason": reason,
            "checks": checks,
            "needs_human_approval": True,
        }

    def check_versioning(self, contract: ProjectContract, changelog: str = "") -> dict[str, Any]:
        """Check if a new version can be created.

        Args:
            contract: The current contract.
            changelog: Proposed changelog.

        Returns:
            Dict with keys: allowed (bool), reason (str).
        """
        if contract.status == ContractStatus.DRAFT:
            return {"allowed": False, "reason": "Draft contracts cannot be versioned. Finalize first."}

        if not changelog:
            return {"allowed": False, "reason": "Changelog is required for versioning."}

        return {"allowed": True, "reason": ""}

    def check_archival(self, contract: ProjectContract) -> dict[str, Any]:
        """Check if a contract can be archived.

        Args:
            contract: The contract to check.

        Returns:
            Dict with keys: allowed (bool), reason (str).
        """
        if contract.status not in (ContractStatus.FINALIZED, ContractStatus.SUPERSEDED):
            return {"allowed": False, "reason": "Only finalized or superseded contracts can be archived."}

        return {"allowed": True, "reason": ""}
