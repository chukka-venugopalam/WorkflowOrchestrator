"""Contract diff — compute differences between contract versions.

Supports:
- Field-level diffs of contract data
- List diffs (added/removed items)
- Summary generation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from workflow_orchestrator.contracts.contract_schema import ContractData, ContractStatus
from workflow_orchestrator.contracts.project_contract import ProjectContract

logger = logging.getLogger(__name__)


@dataclass
class DiffResult:
    """Result of comparing two contract versions.

    Attributes:
        from_version: Source version.
        to_version: Target version.
        changes: List of human-readable change descriptions.
        additions: Items that were added.
        removals: Items that were removed.
        modifications: Fields that changed.
        breaking: Whether any changes are breaking.
    """

    from_version: str = ""
    to_version: str = ""
    changes: list[str] = field(default_factory=list)
    additions: list[str] = field(default_factory=list)
    removals: list[str] = field(default_factory=list)
    modifications: list[str] = field(default_factory=list)
    breaking: bool = False


class ContractDiffer:
    """Computes differences between contract versions.

    Usage:
        >>> differ = ContractDiffer()
        >>> result = differ.compare(old_contract, new_contract)
        >>> for change in result.changes:
        ...     print(change)
    """

    def compare(self, old: ProjectContract, new: ProjectContract) -> DiffResult:
        """Compare two contract versions and produce a diff.

        Args:
            old: The older contract version.
            new: The newer contract version.

        Returns:
            DiffResult with all changes.
        """
        result = DiffResult(
            from_version=old.version,
            to_version=new.version,
        )

        # Compare scalar fields
        if old.data.vision != new.data.vision:
            result.modifications.append("vision")
            if old.data.vision and new.data.vision:
                result.changes.append(f"Vision updated (was: '{old.data.vision[:50]}...')")
            elif new.data.vision:
                result.additions.append("Vision defined")

        if old.data.architecture != new.data.architecture:
            result.modifications.append("architecture")
            result.changes.append("Architecture updated")

        if old.data.folder_structure != new.data.folder_structure:
            result.modifications.append("folder_structure")
            result.changes.append("Folder structure updated")

        if old.data.coding_standards != new.data.coding_standards:
            result.modifications.append("coding_standards")
            result.changes.append("Coding standards updated")

        # Compare lists
        added_reqs = set(new.data.requirements) - set(old.data.requirements)
        removed_reqs = set(old.data.requirements) - set(new.data.requirements)

        for req in added_reqs:
            result.additions.append(f"Requirement: {req[:100]}")
            result.changes.append(f"Added requirement: {req[:100]}")

        for req in removed_reqs:
            result.removals.append(f"Requirement: {req[:100]}")
            result.changes.append(f"Removed requirement: {req[:100]}")

        if added_reqs or removed_reqs:
            result.modifications.append("requirements")

        # Compare constraints
        old_constraints = {(c.category, c.description) for c in old.data.constraints}
        new_constraints = {(c.category, c.description) for c in new.data.constraints}

        added_constraints = new_constraints - old_constraints
        removed_constraints = old_constraints - new_constraints

        for cat, desc in added_constraints:
            result.additions.append(f"Constraint ({cat}): {desc[:100]}")
            result.changes.append(f"Added constraint '{desc[:50]}'")
            result.breaking = True  # Constraint changes are breaking

        for cat, desc in removed_constraints:
            result.removals.append(f"Constraint ({cat}): {desc[:100]}")

        if added_constraints or removed_constraints:
            result.modifications.append("constraints")

        # Compare acceptance criteria
        old_criteria = {c.id for c in old.data.acceptance_criteria}
        new_criteria = {c.id for c in new.data.acceptance_criteria}

        for cid in new_criteria - old_criteria:
            result.additions.append(f"Acceptance criterion: {cid}")
            result.changes.append(f"Added acceptance criterion '{cid}'")

        for cid in old_criteria - new_criteria:
            result.removals.append(f"Acceptance criterion: {cid}")

        if new_criteria != old_criteria:
            result.modifications.append("acceptance_criteria")
            result.breaking = True

        return result
