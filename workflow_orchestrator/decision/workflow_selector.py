"""Workflow selector — selects workflows based on goals and project state.

The selector matches goals to available workflow definitions using:
- Goal keyword matching
- Capability requirements
- Project phase compatibility
- Workflow tags and metadata

No workflow names are hardcoded. Selection is rule-based.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.decision.decision_models import (
    DecisionContext,
    ProjectPhase,
    WorkflowSelection,
)

logger = logging.getLogger(__name__)

# Phase-to-capability mapping
_PHASE_CAPABILITIES: dict[str, list[str]] = {
    "discovery": ["tool.project-scan", "reasoning.analysis", "tool.git"],
    "planning": ["reasoning.architecture", "reasoning.planning", "codegen.design"],
    "coding": ["codegen.general", "codegen.python", "codegen.nextjs", "codegen.frontend", "codegen.backend"],
    "verification": ["verify.build", "verify.test", "verify.lint", "verify.code-review"],
    "deployment": ["deploy.vercel", "deploy.render", "deploy.docker", "verify.smoke-test"],
    "maintenance": ["tool.git", "reasoning.code-review", "verify.lint"],
}

# Default built-in workflow templates
_DEFAULT_WORKFLOWS: list[dict[str, Any]] = [
    {
        "name": "build",
        "description": "Build and test the project",
        "tags": ["build", "test", "verify"],
        "capabilities": ["verify.build", "verify.test"],
        "phases": ["coding", "verification"],
        "source": "workflows/example.yaml",
    },
    {
        "name": "code-review",
        "description": "Run code review on recent changes",
        "tags": ["review", "quality"],
        "capabilities": ["reasoning.code-review", "verify.lint"],
        "phases": ["coding", "verification", "maintenance"],
        "source": "",
    },
    {
        "name": "deploy",
        "description": "Deploy to production",
        "tags": ["deploy", "production"],
        "capabilities": ["deploy.vercel", "verify.smoke-test"],
        "phases": ["deployment"],
        "source": "",
    },
    {
        "name": "setup",
        "description": "Initialize project setup",
        "tags": ["setup", "init"],
        "capabilities": ["tool.project-scan", "tool.git"],
        "phases": ["discovery", "planning"],
        "source": "",
    },
]


class WorkflowSelector:
    """Selects workflows based on goals, project state, and capabilities.

    Usage:
        >>> selector = WorkflowSelector()
        >>> selection = selector.select_for_goal(
        ...     goal="build and deploy the landing page",
        ...     context=context,
        ... )
        >>> print(selection.workflow_name)
    """

    def __init__(self, workflow_dir: Path | str | None = None) -> None:
        """Initialize the workflow selector.

        Args:
            workflow_dir: Optional directory with workflow YAML files.
        """
        self._workflow_dir = Path(workflow_dir) if workflow_dir else None
        self._workflows: list[dict[str, Any]] = list(_DEFAULT_WORKFLOWS)

    def register_workflow(self, name: str, description: str = "", tags: list[str] | None = None,
                           capabilities: list[str] | None = None, phases: list[str] | None = None,
                           source: str = "") -> None:
        """Register a custom workflow for selection.

        Args:
            name: Workflow name.
            description: Description of what the workflow does.
            tags: Tags for matching.
            capabilities: Capabilities this workflow requires.
            phases: Compatible project phases.
            source: Source file path.
        """
        self._workflows.append({
            "name": name,
            "description": description,
            "tags": tags or [],
            "capabilities": capabilities or [],
            "phases": phases or [],
            "source": source,
        })

    def select_for_goal(
        self,
        goal: str,
        context: DecisionContext,
    ) -> WorkflowSelection:
        """Select the best workflow for a given goal.

        Args:
            goal: The user's goal description.
            context: The decision context.

        Returns:
            A WorkflowSelection with the best matching workflow.
        """
        goal_lower = goal.lower()
        scored: list[tuple[float, dict[str, Any]]] = []

        for wf in self._workflows:
            score = self._score_workflow(wf, goal_lower, context)
            if score > 0:
                scored.append((score, wf))

        if not scored:
            return WorkflowSelection(
                confidence=0.0,
                required_capabilities=self._get_phase_capabilities(context.project_phase),
                reasoning=f"No workflow matched goal '{goal}' for phase '{context.project_phase.value}'",
            )

        scored.sort(key=lambda x: (-x[0], x[1]["name"]))
        best_score, best_wf = scored[0]

        return WorkflowSelection(
            workflow_name=best_wf["name"],
            workflow_source=best_wf.get("source", ""),
            confidence=best_score / 2.0,  # Normalize: max raw score is ~2.0
            required_capabilities=best_wf.get("capabilities", []),
            reasoning=f"Selected workflow '{best_wf['name']}' (score={best_score:.2f}) "
                      f"for goal '{goal}' in phase '{context.project_phase.value}'",
        )

    def _score_workflow(self, wf: dict[str, Any], goal_lower: str, context: DecisionContext) -> float:
        """Score a workflow for a given goal and context.

        Args:
            wf: The workflow definition.
            goal_lower: Lowercase goal string.
            context: The decision context.

        Returns:
            Score (higher = better match).
        """
        score = 0.0

        # Phase compatibility
        phase_value = context.project_phase.value
        if phase_value in wf.get("phases", []):
            score += 0.5

        # Goal keyword matching
        goal_words = set(goal_lower.split())
        wf_words = set(wf.get("name", "").lower().split())
        desc_words = set(wf.get("description", "").lower().split())

        name_overlap = len(goal_words & wf_words)
        desc_overlap = len(goal_words & desc_words)

        score += name_overlap * 0.3
        score += desc_overlap * 0.1

        # Tag matching
        goal_tags = {w for w in goal_words if w in {"build", "test", "deploy", "review", "setup", "init", "scan"}}
        wf_tags = set(wf.get("tags", []))
        tag_overlap = len(goal_tags & wf_tags)
        score += tag_overlap * 0.2

        # Capability overlap with context
        context_caps = set(context.available_capabilities)
        wf_caps = set(wf.get("capabilities", []))
        if context_caps and wf_caps:
            cap_overlap = len(context_caps & wf_caps)
            score += cap_overlap * 0.1

        return score

    def select_for_phase(
        self,
        phase: ProjectPhase,
        context: DecisionContext,
    ) -> list[WorkflowSelection]:
        """Select all workflows compatible with a project phase.

        Args:
            phase: The project phase.
            context: The decision context.

        Returns:
            List of WorkflowSelection objects, sorted by relevance.
        """
        phase_value = phase.value
        suitable: list[tuple[float, dict[str, Any]]] = []

        for wf in self._workflows:
            if phase_value in wf.get("phases", []):
                score = 1.0
                wf_caps = set(wf.get("capabilities", []))
                context_caps = set(context.available_capabilities)
                if context_caps and wf_caps:
                    score += len(context_caps & wf_caps) * 0.1
                suitable.append((score, wf))

        suitable.sort(key=lambda x: (-x[0], x[1]["name"]))
        return [
            WorkflowSelection(
                workflow_name=wf["name"],
                workflow_source=wf.get("source", ""),
                confidence=min(score / 2.0, 1.0),
                required_capabilities=wf.get("capabilities", []),
                reasoning=f"Workflow '{wf['name']}' is compatible with phase '{phase_value}'",
            )
            for score, wf in suitable
        ]

    def _get_phase_capabilities(self, phase: ProjectPhase) -> list[str]:
        """Get capabilities typically needed for a project phase.

        Args:
            phase: The project phase.

        Returns:
            List of capability IDs.
        """
        return _PHASE_CAPABILITIES.get(phase.value, [])
