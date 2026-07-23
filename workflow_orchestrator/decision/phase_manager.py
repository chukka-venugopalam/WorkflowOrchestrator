"""Phase manager — determines the current project phase based on state and goals.

The phase manager analyzes:
- Execution history (completed/failed steps)
- Current workflow state
- User's goal
- Available capabilities
- Error patterns

Phase detection is entirely deterministic — no AI reasoning.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.decision.decision_models import (
    DecisionContext,
    ProjectPhase,
)

logger = logging.getLogger(__name__)

# Keyword patterns for phase detection
_PHASE_KEYWORDS: dict[str, list[str]] = {
    "discovery": ["scan", "analyze", "explore", "discover", "audit", "inspect", "understand"],
    "planning": ["plan", "design", "architect", "outline", "strategy", "blueprint", "spec"],
    "coding": ["code", "implement", "build", "develop", "write", "program", "create", "feature", "fix", "add"],
    "verification": ["test", "verify", "validate", "check", "review", "lint", "qa", "quality"],
    "deployment": ["deploy", "release", "publish", "ship", "launch", "production", "ci", "cd"],
    "maintenance": ["update", "upgrade", "patch", "refactor", "migrate", "maintain", "optimize"],
}

# Phase transition rules
_PHASE_TRANSITIONS: dict[ProjectPhase, list[ProjectPhase]] = {
    ProjectPhase.UNKNOWN: [ProjectPhase.DISCOVERY, ProjectPhase.PLANNING],
    ProjectPhase.DISCOVERY: [ProjectPhase.PLANNING, ProjectPhase.CODING],
    ProjectPhase.PLANNING: [ProjectPhase.CODING],
    ProjectPhase.CODING: [ProjectPhase.VERIFICATION, ProjectPhase.DEPLOYMENT],
    ProjectPhase.VERIFICATION: [ProjectPhase.CODING, ProjectPhase.DEPLOYMENT],
    ProjectPhase.DEPLOYMENT: [ProjectPhase.VERIFICATION, ProjectPhase.MAINTENANCE],
    ProjectPhase.MAINTENANCE: [ProjectPhase.CODING],
}


class PhaseManager:
    """Determines the current project phase based on state and goals.

    The phase manager is deterministic — it uses only rule-based
    analysis of execution state, goals, and available capabilities.

    Usage:
        >>> manager = PhaseManager()
        >>> phase = manager.determine_phase(
        ...     goal="build a new feature",
        ...     completed_steps=["step_1", "step_2"],
        ...     context=context,
        ... )
        >>> print(phase.value)
        'coding'
    """

    def determine_phase(
        self,
        goal: str = "",
        completed_steps: list[str] | None = None,
        context: DecisionContext | None = None,
    ) -> ProjectPhase:
        """Determine the current project phase.

        Args:
            goal: The user's goal description.
            completed_steps: Steps that have been completed.
            context: Optional decision context for richer analysis.

        Returns:
            The determined ProjectPhase.
        """
        steps = completed_steps or []
        if context:
            steps = context.completed_steps or steps

        # Score each phase
        scores: dict[ProjectPhase, float] = {phase: 0.0 for phase in ProjectPhase}

        # 1. Goal keyword scoring
        if goal:
            goal_lower = goal.lower()
            for phase, keywords in _PHASE_KEYWORDS.items():
                phase_enum = ProjectPhase(phase) if phase in {p.value for p in ProjectPhase} else ProjectPhase.UNKNOWN
                for kw in keywords:
                    if kw in goal_lower:
                        scores[phase_enum] = scores.get(phase_enum, 0.0) + 0.3

        # 2. Execution state scoring
        if context:
            self._score_from_execution_state(context, scores)

        # 3. Step completion scoring
        if steps:
            self._score_from_steps(steps, scores)

        # 4. Available capabilities scoring
        if context and context.available_capabilities:
            self._score_from_capabilities(context, scores)

        # Find the phase with the highest score
        if max(scores.values()) <= 0:
            return ProjectPhase.UNKNOWN

        best_phase = max(scores, key=scores.get)  # type: ignore[type-var]
        best_score = scores[best_phase]

        # If there's a tie, check if transition is valid from context
        if context and context.project_phase != ProjectPhase.UNKNOWN:
            current = context.project_phase
            allowed = _PHASE_TRANSITIONS.get(current, [])
            if best_phase != current and best_phase not in allowed:
                # Score is high for a non-allowed transition — stay in current
                return current

        logger.debug(
            "Determined phase: %s (score=%.2f, alternatives: %s)",
            best_phase.value,
            best_score,
            {p.value: round(s, 2) for p, s in sorted(scores.items(), key=lambda x: -x[1]) if s > 0},
        )
        return best_phase

    def _score_from_execution_state(
        self,
        context: DecisionContext,
        scores: dict[ProjectPhase, float],
    ) -> None:
        """Score phases based on execution state.

        Args:
            context: The decision context.
            scores: Phase scores to update.
        """
        if context.execution_status == "completed":
            if context.failed_steps:
                scores[ProjectPhase.CODING] += 0.5
            else:
                scores[ProjectPhase.MAINTENANCE] += 0.5

        elif context.execution_status == "running":
            if context.completed_steps:
                scores[ProjectPhase.CODING] += 0.3
                scores[ProjectPhase.VERIFICATION] += 0.2

        elif context.execution_status == "failed":
            scores[ProjectPhase.CODING] += 0.4
            scores[ProjectPhase.VERIFICATION] += 0.3

    def _score_from_steps(
        self,
        steps: list[str],
        scores: dict[ProjectPhase, float],
    ) -> None:
        """Score phases based on completed step names.

        Args:
            steps: List of completed step names/IDs.
            scores: Phase scores to update.
        """
        steps_text = " ".join(s.lower() for s in steps)

        for phase, keywords in _PHASE_KEYWORDS.items():
            phase_enum = ProjectPhase(phase) if phase in {p.value for p in ProjectPhase} else ProjectPhase.UNKNOWN
            for kw in keywords:
                if kw in steps_text:
                    scores[phase_enum] = scores.get(phase_enum, 0.0) + 0.2

    def _score_from_capabilities(
        self,
        context: DecisionContext,
        scores: dict[ProjectPhase, float],
    ) -> None:
        """Score phases based on available capabilities.

        Args:
            context: The decision context.
            scores: Phase scores to update.
        """
        caps_text = " ".join(context.available_capabilities).lower()

        for phase, keywords in _PHASE_KEYWORDS.items():
            phase_enum = ProjectPhase(phase) if phase in {p.value for p in ProjectPhase} else ProjectPhase.UNKNOWN
            for kw in keywords:
                if kw in caps_text:
                    scores[phase_enum] = scores.get(phase_enum, 0.0) + 0.1

    def can_transition(self, current: ProjectPhase, target: ProjectPhase) -> bool:
        """Check if a phase transition is valid.

        Args:
            current: The current project phase.
            target: The target project phase.

        Returns:
            True if the transition is valid.
        """
        if current == target:
            return True
        allowed = _PHASE_TRANSITIONS.get(current, [])
        return target in allowed
