"""Capability matcher for the Intelligence Plane.

Given a set of required capabilities (planning, vision, coding,
large_context, reasoning, etc.), returns ranked provider-agent
candidates that can fulfill them.

Everything is capability-based. No provider names are hardcoded.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from workflow_orchestrator.intelligence.agent_registry import AgentRegistry
from workflow_orchestrator.intelligence.models import (
    Capability,
    RoutingCandidate,
)
from workflow_orchestrator.intelligence.provider_registry import ProviderRegistry

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of a capability matching operation.

    Attributes:
        required_capabilities: The capabilities that were required.
        candidates: Ranked list of routing candidates.
        unmatched_capabilities: Capabilities that no provider-agent pair could fulfill.
        trace: Detailed matching trace for debugging.
    """

    required_capabilities: list[str] = field(default_factory=list)
    candidates: list[RoutingCandidate] = field(default_factory=list)
    unmatched_capabilities: list[str] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)


class CapabilityMatcher:
    """Matches required capabilities to provider-agent pairs.

    The matching algorithm:
    1. For each required capability, find providers that offer it
    2. For each matching provider, find agents that support it
    3. Score each provider-agent pair by coverage
    4. Return ranked candidates

    No provider names are hardcoded. Everything is capability-based.
    """

    def __init__(
        self,
        provider_registry: ProviderRegistry,
        agent_registry: AgentRegistry,
    ) -> None:
        """Initialize the capability matcher.

        Args:
            provider_registry: Registry of available providers.
            agent_registry: Registry of available agents.
        """
        self._provider_registry = provider_registry
        self._agent_registry = agent_registry

    # ------------------------------------------------------------------
    # Main matching
    # ------------------------------------------------------------------

    def match(
        self,
        required_capabilities: list[str],
        min_coverage: float = 0.5,
    ) -> MatchResult:
        """Match required capabilities to provider-agent pairs.

        Args:
            required_capabilities: List of capability IDs needed.
            min_coverage: Minimum fraction of capabilities that must
                be covered for a candidate to be included.

        Returns:
            MatchResult with ranked candidates and unmatched capabilities.
        """
        trace: list[str] = []
        candidates: list[RoutingCandidate] = []
        all_matched: set[str] = set()
        total_required = len(required_capabilities)

        trace.append(f"Matching {total_required} required capabilities: {required_capabilities}")

        if total_required == 0:
            trace.append("No capabilities required — returning empty match")
            return MatchResult(
                required_capabilities=[],
                candidates=[],
                unmatched_capabilities=[],
                trace=trace,
            )

        # Build a combined index of (provider, agent) -> matched capabilities
        pair_scores: dict[tuple[str, str], set[str]] = {}

        for cap_id in required_capabilities:
            # Find providers offering this capability
            providers = self._provider_registry.find_by_capability(cap_id)
            if not providers:
                trace.append(f"  Capability '{cap_id}': no matching providers found")
                continue

            trace.append(f"  Capability '{cap_id}': found {len(providers)} provider(s)")

            for provider in providers:
                pid = provider.provider_id

                # Find agents supporting this capability
                agents = self._agent_registry.find_by_capability(cap_id)
                if not agents:
                    trace.append(f"    Provider '{pid}': no matching agents found")
                    continue

                for agent in agents:
                    aid = agent.agent_id
                    pair_scores.setdefault((pid, aid), set()).add(cap_id)
                    all_matched.add(cap_id)
                    trace.append(f"    Pair ({pid}, {aid}): matched '{cap_id}'")

        # Build ranked candidates from pair scores
        for (pid, aid), matched_caps in pair_scores.items():
            coverage = len(matched_caps) / total_required if total_required > 0 else 0.0
            if coverage < min_coverage:
                trace.append(f"  Excluded pair ({pid}, {aid}): coverage {coverage:.0%} < {min_coverage:.0%}")
                continue

            candidate = RoutingCandidate(
                provider_id=pid,
                agent_id=aid,
                matched_capabilities=sorted(matched_caps),
                score=coverage,
            )
            candidates.append(candidate)

        # Sort by score descending, then by number of matched capabilities
        candidates.sort(key=lambda c: (-c.score, -len(c.matched_capabilities)))
        trace.append(f"Generated {len(candidates)} candidate(s) sorted by score")

        # Identify unmatched capabilities
        unmatched = [c for c in required_capabilities if c not in all_matched]
        if unmatched:
            trace.append(f"Unmatched capabilities: {unmatched}")

        return MatchResult(
            required_capabilities=required_capabilities,
            candidates=candidates,
            unmatched_capabilities=unmatched,
            trace=trace,
        )

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    def find_providers_for_capability(self, capability_id: str) -> list[str]:
        """Find all providers that offer a specific capability.

        Args:
            capability_id: The capability ID.

        Returns:
            List of provider IDs.
        """
        providers = self._provider_registry.find_by_capability(capability_id)
        return [p.provider_id for p in providers]

    def find_agents_for_capability(self, capability_id: str) -> list[str]:
        """Find all agents that support a specific capability.

        Args:
            capability_id: The capability ID.

        Returns:
            List of agent IDs.
        """
        agents = self._agent_registry.find_by_capability(capability_id)
        return [a.agent_id for a in agents]

    def coverage_report(self) -> dict[str, Any]:
        """Generate a coverage report of all capabilities vs providers/agents.

        Returns:
            Dict with coverage analysis.
        """
        provider_caps = self._provider_registry.all_capabilities()
        agent_caps = self._agent_registry.all_capabilities()

        # Aggregate all known capabilities
        all_caps: set[str] = set()
        provider_cov: dict[str, set[str]] = {}
        agent_cov: dict[str, set[str]] = {}

        for pid, caps in provider_caps.items():
            cap_ids = {c.id for c in caps}
            all_caps.update(cap_ids)
            provider_cov[pid] = cap_ids

        for aid, caps in agent_caps.items():
            cap_ids = {c.id for c in caps}
            all_caps.update(cap_ids)
            agent_cov[aid] = cap_ids

        # Coverage per capability
        cap_coverage: dict[str, dict[str, int]] = {}
        for cap in sorted(all_caps):
            p_count = sum(1 for cov in provider_cov.values() if cap in cov)
            a_count = sum(1 for cov in agent_cov.values() if cap in cov)
            cap_coverage[cap] = {"providers": p_count, "agents": a_count}

        return {
            "total_capabilities": len(all_caps),
            "total_providers": len(provider_caps),
            "total_agents": len(agent_caps),
            "capability_coverage": cap_coverage,
        }
