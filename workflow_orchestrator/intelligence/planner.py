"""Planner for the Intelligence Plane.

The Planner produces plans (ordered sequences of steps) from goals.
This is a skeleton that will be enriched in later phases when
the Decision Engine is implemented.

Currently supports:
- Simple step decomposition from a goal
- Plan validation
- Required capability extraction

No provider-specific logic. No execution.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.intelligence.models import (
    Capability,
    Plan,
)
from workflow_orchestrator.intelligence.capability_matcher import CapabilityMatcher

logger = logging.getLogger(__name__)


class Planner:
    """Produces plans from goals.

    A plan is an ordered sequence of steps with required capabilities.
    This skeleton will be extended in later phases with the full
    Decision Engine.

    Usage:
        >>> planner = Planner()
        >>> plan = planner.plan("Build a landing page with Next.js")
        >>> print(len(plan.steps))
        3
    """

    def __init__(
        self,
        capability_matcher: CapabilityMatcher | None = None,
    ) -> None:
        """Initialize the planner.

        Args:
            capability_matcher: Optional capability matcher for
                capability validation.
        """
        self._capability_matcher = capability_matcher

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------

    def plan(
        self,
        goal: str,
        context: dict[str, Any] | None = None,
    ) -> Plan:
        """Create a plan from a goal.

        This is a simple skeleton that extracts required capabilities
        from the goal. Future implementations will use the full
        Decision Engine for template-first planning.

        Args:
            goal: The goal or task description.
            context: Optional context for planning.

        Returns:
            A Plan with steps and required capabilities.
        """
        context = context or {}

        # Simple step decomposition based on common patterns
        steps, capabilities = self._decompose_goal(goal)

        plan = Plan(
            goal=goal,
            steps=steps,
            required_capabilities=capabilities,
            estimated_steps=len(steps),
            metadata={"source": "planner_skeleton", **context},
        )

        logger.debug("Created plan for goal: '%s' (%d steps)", goal[:50], len(steps))
        return plan

    def _decompose_goal(
        self,
        goal: str,
    ) -> tuple[list[str], list[str]]:
        """Decompose a goal into steps and required capabilities.

        This is a simple rule-based decomposition using placeholder
        capability IDs (``codegen.general``, ``reasoning.general``,
        ``verify.general``).  These are *not* provider names — they
        are generic capability identifiers that will be replaced by
        the full Decision Engine in later phases.

        Args:
            goal: The goal to decompose.

        Returns:
            Tuple of (steps list, capabilities list).
        """
        goal_lower = goal.lower()
        steps: list[str] = []
        capabilities: list[str] = []

        # Detect code generation needs
        if any(kw in goal_lower for kw in ["build", "create", "implement", "generate", "develop", "code"]):
            capabilities.append("codegen.general")

        # Detect reasoning needs
        if any(kw in goal_lower for kw in ["analyze", "review", "explain", "design", "architecture"]):
            capabilities.append("reasoning.general")

        # Detect verification needs
        if any(kw in goal_lower for kw in ["test", "verify", "check", "lint", "validate"]):
            capabilities.append("verify.general")

        # If no specific capabilities detected, add a general one
        if not capabilities:
            capabilities.append("reasoning.general")

        # Create steps
        steps.append(f"Analyze: {goal}")
        steps.append(f"Execute: {goal}")
        steps.append("Verify: Review results")

        return steps, capabilities

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_plan(self, plan: Plan) -> list[str]:
        """Validate a plan for correctness.

        Args:
            plan: The plan to validate.

        Returns:
            List of validation errors (empty if valid).
        """
        errors: list[str] = []

        if not plan.goal:
            errors.append("Plan has no goal")

        if not plan.steps:
            errors.append("Plan has no steps")

        if not plan.required_capabilities:
            errors.append("Plan has no required capabilities")

        # Validate capabilities with the matcher
        if self._capability_matcher and plan.required_capabilities:
            for cap_id in plan.required_capabilities:
                providers = self._capability_matcher.find_providers_for_capability(cap_id)
                if not providers:
                    errors.append(f"Capability '{cap_id}' has no available providers")

        return errors

    def is_valid(self, plan: Plan) -> bool:
        """Quick check if a plan is valid.

        Args:
            plan: The plan to check.

        Returns:
            True if the plan has no validation errors.
        """
        return len(self.validate_plan(plan)) == 0
