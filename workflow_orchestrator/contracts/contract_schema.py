"""Contract schema — schema definitions for Project Contract.

Defines the data models for:
- Vision, Requirements, Architecture
- Folder Structure, Coding Standards
- Tech Stack, Constraints
- Milestones, Acceptance Criteria
- Human Decisions, Version History
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ContractStatus(Enum):
    """Lifecycle status of a project contract."""

    DRAFT = "draft"
    FINALIZED = "finalized"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class TechStack:
    """Declared technology stack.

    Attributes:
        framework: Web/app framework (e.g., "Next.js").
        language: Primary language (e.g., "Python", "TypeScript").
        styling: Styling approach (e.g., "Tailwind CSS").
        deployment: Deployment platform (e.g., "Vercel").
        database: Database technology (e.g., "PostgreSQL").
        testing: Testing frameworks.
        ci_cd: CI/CD platform.
        additional: Additional tools/technologies.
    """

    framework: str = ""
    language: str = ""
    styling: str = ""
    deployment: str = ""
    database: str = ""
    testing: str = ""
    ci_cd: str = ""
    additional: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Constraint:
    """An immutable project constraint.

    Attributes:
        category: Constraint category (e.g., "performance", "security").
        description: Description of the constraint.
        severity: Severity (must, should, nice-to-have).
    """

    category: str = ""
    description: str = ""
    severity: str = "must"


@dataclass(frozen=True)
class AcceptanceCriterion:
    """An acceptance criterion for verification.

    Attributes:
        id: Unique criterion identifier.
        description: Description of the criterion.
        category: Category (e.g., "functional", "performance").
        verification_type: How to verify (e.g., "test", "manual", "build").
    """

    id: str = ""
    description: str = ""
    category: str = "functional"
    verification_type: str = "manual"


@dataclass(frozen=True)
class ContractMilestone:
    """A project milestone.

    Attributes:
        name: Milestone name.
        description: Description.
        criteria: Acceptance criteria IDs that define completion.
        completed: Whether this milestone is complete.
    """

    name: str = ""
    description: str = ""
    criteria: list[str] = field(default_factory=list)
    completed: bool = False


@dataclass(frozen=True)
class StyleConvention:
    """A coding style convention.

    Attributes:
        rule: The rule description.
        scope: Scope (e.g., "global", "python", "typescript").
        severity: Severity (required, recommended, optional).
    """

    rule: str = ""
    scope: str = "global"
    severity: str = "recommended"


@dataclass(frozen=True)
class HumanDecision:
    """A human decision recorded in the contract.

    Attributes:
        decision: The decision made.
        rationale: Why the decision was made.
        made_by: Who made the decision.
        date: ISO-8601 date.
        alternatives: Alternative options considered.
    """

    decision: str = ""
    rationale: str = ""
    made_by: str = ""
    date: str = ""
    alternatives: list[str] = field(default_factory=list)


@dataclass
class ContractData:
    """The core data of a project contract.

    This is mutable during drafting but frozen once finalized.

    Attributes:
        vision: Project vision statement.
        requirements: List of requirements.
        architecture: Architecture description.
        folder_structure: Folder structure description.
        coding_standards: Coding standards.
        tech_stack: Tech stack declaration.
        constraints: Project constraints.
        milestones: Project milestones.
        acceptance_criteria: Acceptance criteria.
        style_conventions: Style conventions.
        human_decisions: Human decisions recorded.
    """

    vision: str = ""
    requirements: list[str] = field(default_factory=list)
    architecture: str = ""
    folder_structure: str = ""
    coding_standards: str = ""
    tech_stack: TechStack = field(default_factory=TechStack)
    constraints: list[Constraint] = field(default_factory=list)
    milestones: list[ContractMilestone] = field(default_factory=list)
    acceptance_criteria: list[AcceptanceCriterion] = field(default_factory=list)
    style_conventions: list[StyleConvention] = field(default_factory=list)
    human_decisions: list[HumanDecision] = field(default_factory=list)
