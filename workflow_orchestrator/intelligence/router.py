"""Router for selecting the best provider and agent for a given set of capabilities.

The Router takes required capabilities as input and produces a routing
decision with the best provider-agent pair. It does NOT execute anything
— it only makes routing decisions.

Everything is capability-based. No provider names are hardcoded.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.intelligence.capability_matcher import (
    CapabilityMatcher,
    MatchResult,
)
from workflow_orchestrator.intelligence.models import (
    RoutingCandidate,
    RoutingDecision,
)

logger = logging.getLogger(__name__)


class Router:
    """Routes capability requirements to the best provider-agent pair.

    The routing algorithm:
    1. Match required capabilities to provider-agent pairs
    2. Score candidates by coverage, cost, and latency
    3. Select the best candidate
    4. Return a RoutingDecision with reasoning

    Usage:
        >>> router = Router(capability_matcher)
        >>> decision = router.route(["reasoning.code-review", "codegen.python"])
        >>> print(decision.selected_provider_id)
        'anthropic.claude'
        >>> print(decision.selected_agent_id)
        'claude-code'
    """

    def __init__(
        self,
        capability_matcher: CapabilityMatcher,
    ) -> None:
        """Initialize the router.

        Args:
            capability_matcher: The capability matcher instance.
        """
        self._matcher = capability_matcher

    # ------------------------------------------------------------------
    # Primary routing
    # ------------------------------------------------------------------

    async def route(
        self,
        required_capabilities: list[str],
        preferred_provider: str | None = None,
        preferred_agent: str | None = None,
        min_coverage: float = 0.5,
    ) -> RoutingDecision:
        """Route required capabilities to the best provider-agent pair.

        Args:
            required_capabilities: List of capability IDs needed.
            preferred_provider: Optional preferred provider ID.
            preferred_agent: Optional preferred agent ID.
            min_coverage: Minimum capability coverage fraction (0.0 to 1.0).

        Returns:
            RoutingDecision with selected provider, agent, and reasoning.
        """
        trace: list[str] = []

        trace.append(f"Routing for capabilities: {required_capabilities}")
        if preferred_provider:
            trace.append(f"Preferred provider: {preferred_provider}")
        if preferred_agent:
            trace.append(f"Preferred agent: {preferred_agent}")

        # Step 1: Match capabilities to candidates
        match_result = self._matcher.match(
            required_capabilities=required_capabilities,
            min_coverage=min_coverage,
        )
        trace.extend(f"  [match] {t}" for t in match_result.trace)

        candidates = match_result.candidates
        if not candidates:
            trace.append("No candidates found for the required capabilities")
            return RoutingDecision(
                required_capabilities=required_capabilities,
                selected_provider_id="",
                selected_agent_id="",
                confidence=0.0,
                reasoning="No provider-agent pair can fulfill the required capabilities.",
                trace=trace,
            )

        # Step 2: Apply preferences
        if preferred_provider:
            preferred = [c for c in candidates if c.provider_id == preferred_provider]
            if preferred:
                candidates = preferred
                trace.append(f"Filtered to preferred provider '{preferred_provider}' ({len(candidates)} candidates)")

        if preferred_agent:
            preferred = [c for c in candidates if c.agent_id == preferred_agent]
            if preferred:
                candidates = preferred
                trace.append(f"Filtered to preferred agent '{preferred_agent}' ({len(candidates)} candidates)")

        # Step 3: Select the best candidate
        best = candidates[0]
        trace.append(f"Selected: provider='{best.provider_id}', agent='{best.agent_id}' (score={best.score:.2f})")

        # Build alternatives list
        alternatives = [
            {
                "provider_id": c.provider_id,
                "agent_id": c.agent_id,
                "score": c.score,
                "matched_capabilities": len(c.matched_capabilities),
            }
            for c in candidates[1:4]  # Top 3 alternatives
        ]

        reasoning = (
            f"Selected provider '{best.provider_id}' and agent '{best.agent_id}' "
            f"with capability coverage of {best.score:.0%} "
            f"({len(best.matched_capabilities)}/{len(required_capabilities)} capabilities matched)."
        )

        return RoutingDecision(
            required_capabilities=required_capabilities,
            selected_provider_id=best.provider_id,
            selected_agent_id=best.agent_id,
            confidence=best.score,
            alternatives=alternatives,
            reasoning=reasoning,
            trace=trace,
        )

    # ------------------------------------------------------------------
    # Fallback routing
    # ------------------------------------------------------------------

    async def route_fallback(
        self,
        original_decision: RoutingDecision,
        exclude_providers: list[str] | None = None,
        exclude_agents: list[str] | None = None,
    ) -> RoutingDecision:
        """Fallback routing when the primary choice fails.

        Reroutes the same capabilities but excludes failed providers/agents.

        Args:
            original_decision: The original routing decision that failed.
            exclude_providers: Providers to exclude.
            exclude_agents: Agents to exclude.

        Returns:
            A new RoutingDecision with the fallback choice.
        """
        trace = list(original_decision.trace)
        trace.append(f"Fallback routing requested (exclude providers={exclude_providers}, agents={exclude_agents})")

        # Re-match with preferred exclusions
        match_result = self._matcher.match(
            required_capabilities=original_decision.required_capabilities,
            min_coverage=0.0,  # Lower threshold for fallback
        )

        # Filter out excluded providers and agents
        candidates = match_result.candidates
        if exclude_providers:
            candidates = [c for c in candidates if c.provider_id not in exclude_providers]
        if exclude_agents:
            candidates = [c for c in candidates if c.agent_id not in exclude_agents]

        if not candidates:
            trace.append("No fallback candidates available")
            return RoutingDecision(
                required_capabilities=original_decision.required_capabilities,
                selected_provider_id="",
                selected_agent_id="",
                confidence=0.0,
                reasoning="No fallback provider-agent pair available after exclusions.",
                trace=trace,
            )

        best = candidates[0]
        trace.append(f"Fallback selected: provider='{best.provider_id}', agent='{best.agent_id}'")
        return RoutingDecision(
            required_capabilities=original_decision.required_capabilities,
            selected_provider_id=best.provider_id,
            selected_agent_id=best.agent_id,
            confidence=best.score,
            alternatives=[
                {"provider_id": c.provider_id, "agent_id": c.agent_id, "score": c.score}
                for c in candidates[1:4]
            ],
            reasoning=f"Fallback to provider '{best.provider_id}' and agent '{best.agent_id}'.",
            trace=trace,
        )

    # ------------------------------------------------------------------
    # Batch routing
    # ------------------------------------------------------------------

    async def route_batch(
        self,
        capability_groups: list[list[str]],
    ) -> list[RoutingDecision]:
        """Route multiple capability groups in batch.

        Args:
            capability_groups: List of capability ID groups.

        Returns:
            List of RoutingDecision objects, one per group.
        """
        decisions: list[RoutingDecision] = []
        for group in capability_groups:
            decision = await self.route(group)
            decisions.append(decision)
        return decisions
