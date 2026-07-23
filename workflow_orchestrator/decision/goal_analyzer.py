"""Goal analyzer — analyzes user goals to determine required capabilities.

The goal analyzer is purely rule-based:
- Keyword matching against capability patterns
- Phase-based capability inference
- Constraint extraction from goal text

No AI reasoning, no subjective judgments.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from workflow_orchestrator.decision.decision_models import (
    DecisionContext,
    ProjectPhase,
)

logger = logging.getLogger(__name__)

# Capability detection patterns
# Maps capability IDs to keyword patterns
_CAPABILITY_PATTERNS: dict[str, list[str]] = {
    "codegen.python": ["python", "django", "flask", "fastapi", "pytest", "pip"],
    "codegen.nextjs": ["nextjs", "next.js", "react", "vercel", "ssr"],
    "codegen.frontend": ["frontend", "ui", "component", "css", "html", "javascript", "typescript", "react", "vue", "angular"],
    "codegen.backend": ["backend", "api", "server", "database", "graphql", "rest", "endpoint"],
    "codegen.general": ["code", "implement", "write", "create", "add", "feature", "function"],
    "reasoning.code-review": ["review", "audit", "inspect", "check code", "quality"],
    "reasoning.architecture": ["architecture", "design", "structure", "pattern", "refactor"],
    "reasoning.analysis": ["analyze", "understand", "explain", "document", "research"],
    "reasoning.planning": ["plan", "strategy", "roadmap", "milestone", "sprint"],
    "verify.build": ["build", "compile", "bundle", "package"],
    "verify.test": ["test", "testing", "unit test", "integration test", "e2e"],
    "verify.lint": ["lint", "format", "style", "prettier", "eslint"],
    "deploy.vercel": ["deploy", "vercel", "release", "ship", "production"],
    "deploy.docker": ["docker", "container", "image"],
    "tool.git": ["git", "commit", "push", "pull", "branch", "merge", "clone"],
    "tool.project-scan": ["scan", "analyze project", "understand project", "explore"],
}


class GoalAnalyzer:
    """Analyzes user goals to determine required capabilities.

    The analysis is entirely rule-based — no AI reasoning.
    Patterns are matched deterministically against goal text.

    Usage:
        >>> analyzer = GoalAnalyzer()
        >>> capabilities = analyzer.analyze("build a python api with tests")
        >>> print(capabilities)
        ['codegen.python', 'codegen.backend', 'verify.test']
    """

    def analyze(
        self,
        goal: str,
        context: DecisionContext | None = None,
    ) -> list[str]:
        """Analyze a goal to determine required capabilities.

        Args:
            goal: The user's goal description.
            context: Optional decision context for richer analysis.

        Returns:
            Sorted list of required capability IDs.
        """
        goal_lower = goal.lower()
        matched: set[str] = set()

        # 1. Direct keyword matching
        for capability_id, patterns in _CAPABILITY_PATTERNS.items():
            for pattern in patterns:
                if pattern in goal_lower:
                    matched.add(capability_id)
                    break  # One match per capability is enough

        # 2. Phase-based inference
        if context and context.project_phase != ProjectPhase.UNKNOWN:
            phase_caps = self._get_phase_capabilities(context.project_phase)
            for cap in phase_caps:
                if cap not in matched:
                    logger.debug("Inferred capability '%s' from phase '%s'", cap, context.project_phase.value)
                    matched.add(cap)

        # 3. Execution context inference
        if context and context.failed_steps:
            # If we have failed steps, add verification capabilities
            matched.add("verify.build")
            matched.add("reasoning.code-review")

        # 4. Constraints-based inference
        if context and context.constraints:
            for constraint in context.constraints:
                constraint_lower = constraint.lower()
                for capability_id, patterns in _CAPABILITY_PATTERNS.items():
                    for pattern in patterns:
                        if pattern in constraint_lower:
                            matched.add(capability_id)
                            break

        result = sorted(matched)

        logger.debug(
            "Analyzed goal '%s': matched %d capabilities: %s",
            goal[:50],
            len(result),
            result,
        )
        return result

    def analyze_with_priorities(
        self,
        goal: str,
        context: DecisionContext | None = None,
    ) -> dict[str, float]:
        """Analyze a goal and return capabilities with priority scores.

        Args:
            goal: The user's goal description.
            context: Optional decision context.

        Returns:
            Dict mapping capability ID to priority score (0.0 to 1.0).
        """
        capabilities = self.analyze(goal, context)
        goal_lower = goal.lower()

        priorities: dict[str, float] = {}
        for cap in capabilities:
            # Base priority
            priority = 0.5

            # Boost priority based on keyword overlap strength
            patterns = _CAPABILITY_PATTERNS.get(cap, [])
            matches = sum(1 for p in patterns if p in goal_lower)
            if matches > 0:
                priority = min(0.5 + (matches * 0.1), 1.0)

            priorities[cap] = priority

        return priorities

    def extract_constraints(self, goal: str) -> list[str]:
        """Extract explicit constraints from a goal.

        Args:
            goal: The user's goal description.

        Returns:
            List of extracted constraint descriptions.
        """
        goal_lower = goal.lower()
        constraints: list[str] = []

        # Look for constraint keywords
        constraint_patterns = [
            ("must", "Requirement"),
            ("should", "Recommendation"),
            ("need", "Requirement"),
            ("required", "Requirement"),
            ("optional", "Optional"),
            ("but not", "Exclusion"),
            ("except", "Exclusion"),
            ("without", "Exclusion"),
            ("within", "Time constraint"),
            ("by ", "Deadline"),
        ]

        for keyword, constraint_type in constraint_patterns:
            if keyword in goal_lower:
                # Extract the sentence containing the keyword
                sentences = re.split(r'[.!?\n]', goal)
                for sentence in sentences:
                    if keyword in sentence.lower():
                        constraints.append(f"[{constraint_type}] {sentence.strip()}")

        return constraints

    def _get_phase_capabilities(self, phase: ProjectPhase) -> list[str]:
        """Get capabilities typically needed for a project phase.

        Args:
            phase: The project phase.

        Returns:
            List of capability IDs.
        """
        phase_map = {
            ProjectPhase.DISCOVERY: ["tool.project-scan", "reasoning.analysis", "tool.git"],
            ProjectPhase.PLANNING: ["reasoning.architecture", "reasoning.planning"],
            ProjectPhase.CODING: ["codegen.general"],
            ProjectPhase.VERIFICATION: ["verify.test", "verify.build", "verify.lint", "reasoning.code-review"],
            ProjectPhase.DEPLOYMENT: ["deploy.vercel"],
            ProjectPhase.MAINTENANCE: ["tool.git", "reasoning.code-review"],
            ProjectPhase.UNKNOWN: [],
        }
        return phase_map.get(phase, [])
