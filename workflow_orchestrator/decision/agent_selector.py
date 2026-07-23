"""Agent selector — selects the best agent from available candidates.

The selector evaluates agents based on:
- Capability coverage
- Provider compatibility
- Runtime requirements
- User preferences

No agent names are hardcoded. Everything is capability-based.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.decision.decision_models import (
    AgentSelection,
    DecisionContext,
)
from workflow_orchestrator.decision.routing_policy import RoutingPolicy

logger = logging.getLogger(__name__)


class AgentSelector:
    """Selects the best agent from available candidates.

    The selection is deterministic: given the same context,
    the same agent is always selected.

    Usage:
        >>> selector = AgentSelector()
        >>> selection = selector.select(
        ...     context=context,
        ...     required_capabilities=["codegen.nextjs"],
        ...     preferred_provider="anthropic.claude",
        ... )
        >>> print(selection.agent_id)
    """

    def __init__(self, policy: RoutingPolicy | None = None) -> None:
        """Initialize the agent selector.

        Args:
            policy: Optional routing policy. Uses default if not provided.
        """
        self._policy = policy or RoutingPolicy()

    @property
    def policy(self) -> RoutingPolicy:
        """The routing policy being used."""
        return self._policy

    def select(
        self,
        context: DecisionContext,
        required_capabilities: list[str] | None = None,
        preferred_provider: str | None = None,
        exclude_agents: list[str] | None = None,
    ) -> AgentSelection:
        """Select the best agent from context.

        Args:
            context: The decision context with available agents.
            required_capabilities: Capabilities that must be fulfilled.
            preferred_provider: If set, prefer agents compatible with this provider.
            exclude_agents: Agent IDs to exclude.

        Returns:
            An AgentSelection with the best agent or empty if none found.
        """
        caps = required_capabilities or context.available_capabilities
        exclude = set(exclude_agents or [])

        if not context.available_agents:
            logger.warning("No agents available for selection")
            return AgentSelection(
                reasoning="No agents available in context",
            )

        # Score each agent
        scored: list[tuple[float, str]] = []

        for agent_id in context.available_agents:
            if agent_id in exclude:
                continue

            # Get agent capabilities from context metadata
            agent_caps = context.metadata.get(f"agent_capabilities.{agent_id}", caps)
            if not isinstance(agent_caps, list):
                agent_caps = caps

            # Calculate capability coverage
            matched = set(agent_caps) & set(caps)
            coverage = len(matched) / len(caps) if caps else 0.0

            # Base score from coverage
            score = coverage * 0.5

            # Provider compatibility bonus
            if preferred_provider:
                compatible_providers = context.metadata.get(f"agent_providers.{agent_id}", [preferred_provider])
                if isinstance(compatible_providers, list) and preferred_provider in compatible_providers:
                    score += 0.2

            # Preference bonus from user preferences
            preferred_agents = context.user_preferences.get("preferred_agents", [])
            if isinstance(preferred_agents, list) and agent_id in preferred_agents:
                score += 0.2

            # Runtime compatibility
            requires_local = context.metadata.get(f"agent_requires_local.{agent_id}", False)
            if requires_local and context.constraints:
                has_runtime = any("local" in c.lower() for c in context.constraints)
                if has_runtime:
                    score += 0.1
                else:
                    score -= 0.1

            scored.append((score, agent_id))

        if not scored:
            return AgentSelection(
                reasoning="All agents were excluded or none available",
            )

        # Sort by score descending
        scored.sort(key=lambda x: (-x[0], x[1]))
        best_score, best_agent = scored[0]

        # Calculate matched/unmatched
        best_agent_caps = context.metadata.get(f"agent_capabilities.{best_agent}", caps)
        if isinstance(best_agent_caps, list):
            matched_caps = list(set(best_agent_caps) & set(caps))
            unmatched_caps = list(set(caps) - set(best_agent_caps))
        else:
            matched_caps = list(caps)
            unmatched_caps = []

        logger.debug(
            "Selected agent '%s' (score=%.2f, %d/%d capabilities matched)",
            best_agent,
            best_score,
            len(matched_caps),
            len(caps),
        )

        return AgentSelection(
            agent_id=best_agent,
            confidence=best_score,
            matched_capabilities=matched_caps,
            unmatched_capabilities=unmatched_caps,
            reasoning=f"Selected agent '{best_agent}' with score {best_score:.2f} "
                      f"({len(matched_caps)}/{len(caps)} capabilities matched from {len(scored)} candidates)",
        )
