"""Project Contract system — immutable versioned project specifications.

Supports:
- Vision, Requirements, Architecture
- Folder Structure, Coding Standards
- Tech Stack, Constraints
- Milestones, Acceptance Criteria
- Human Decisions, Version History
- Diffs, Validation, Human Approval Checkpoints
"""

from __future__ import annotations

__all__ = [
    "ProjectContract",
    "ContractManager",
    "ContractValidator",
    "ContractHistory",
    "ContractDiffer",
    "ContractRules",
    "ContractSnapshot",
    "ContractSnapshotManager",
    # Schema
    "ContractData",
    "TechStack",
    "Constraint",
    "AcceptanceCriterion",
    "ContractMilestone",
    "StyleConvention",
    "HumanDecision",
    "ContractStatus",
    "DiffResult",
    "HistoryEntry",
]

from workflow_orchestrator.contracts.project_contract import ProjectContract
from workflow_orchestrator.contracts.contract_manager import ContractManager
from workflow_orchestrator.contracts.contract_validator import ContractValidator
from workflow_orchestrator.contracts.contract_history import ContractHistory, HistoryEntry
from workflow_orchestrator.contracts.contract_diff import ContractDiffer, DiffResult
from workflow_orchestrator.contracts.contract_rules import ContractRules
from workflow_orchestrator.contracts.contract_snapshot import ContractSnapshot, ContractSnapshotManager
from workflow_orchestrator.contracts.contract_schema import (
    ContractData,
    TechStack,
    Constraint,
    AcceptanceCriterion,
    ContractMilestone,
    StyleConvention,
    HumanDecision,
    ContractStatus,
)
