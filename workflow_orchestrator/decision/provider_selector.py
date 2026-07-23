"""Provider selector — selects the best provider from available candidates.

The selector evaluates providers based on:
- Capability coverage (matching required capabilities)
- Cost constraints
- Quality preferences
- User preferences
- Health status

No provider names are hardcoded. Everything is capability-based.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.decision.decision_models import (
    DecisionContext,
    ProviderSelection,
)
from workflow_orchestrator.decision.routing_policy import RoutingPolicy

logger = logging.getLogger(__name__)


class ProviderSelector:
    """Selects the best provider from available candidates.

    The selection is deterministic: given the same context and policy,
    the same provider is always selected.

    Usage:
        >>> selector = ProviderSelector()
        >>> selection = selector.select(
        ...     context=context,
        ...     required_capabilities=["reasoning.code-review", "codegen.python"],
        ... )
        >>> print(selection.provider_id)
    """

    def __init__(self, policy: RoutingPolicy | None = None) -> None:
        """Initialize the provider selector.

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
        exclude_providers: list[str] | None = None,
    ) -> ProviderSelection:
        """Select the best provider from context.

        Args:
            context: The decision context with available providers.
            required_capabilities: Capabilities that must be fulfilled.
            exclude_providers: Provider IDs to exclude.

        Returns:
            A ProviderSelection with the best provider or empty if none found.
        """
        caps = required_capabilities or context.available_capabilities
        exclude = set(exclude_providers or [])

        if not context.available_providers:
            logger.warning("No providers available for selection")
            return ProviderSelection(
                reasoning="No providers available in context",
            )

        # Filter out excluded providers early
        filtered_providers = [p for p in context.available_providers if p not in exclude]
        if not filtered_providers:
            return ProviderSelection(
                reasoning="All providers were excluded or none available",
            )

        if not caps:
            logger.debug("No capabilities required; selecting first available provider")
            first = filtered_providers[0]
            return ProviderSelection(
                provider_id=first,
                confidence=0.5,
                reasoning="No specific capabilities required; selected first available provider",
            )

        # Score each provider
        scored: list[tuple[float, str]] = []
        for provider_id in filtered_providers:

            # Compare provider capabilities (from context) with required
            # In a real system, we'd query the provider registry for exact capabilities
            provider_caps = context.metadata.get(f"provider_capabilities.{provider_id}", caps)
            if isinstance(provider_caps, list):
                matched = set(provider_caps) & set(caps)
                coverage = len(matched) / len(caps) if caps else 0.0
                quality = context.metadata.get(f"provider_quality.{provider_id}", 0.5)
                cost = context.metadata.get(f"provider_cost.{provider_id}", 50.0)
                latency = context.metadata.get(f"provider_latency.{provider_id}", 5000.0)
            else:
                coverage = 0.0
                quality = 0.5
                cost = 50.0
                latency = 5000.0

            score = self._policy.score_provider(
                provider_capabilities=[str(c) for c in (provider_caps if isinstance(provider_caps, list) else caps)],
                required_capabilities=caps,
                estimated_cost=cost,
                estimated_latency_ms=latency,
                quality_score=quality,
            )
            scored.append((score, provider_id))

        if not scored:
            return ProviderSelection(
                reasoning="All providers were excluded or none available",
            )

        # Sort by score descending
        scored.sort(key=lambda x: (-x[0], x[1]))

        best_score, best_provider = scored[0]

        # Calculate matched/unmatched
        best_provider_caps = context.metadata.get(f"provider_capabilities.{best_provider}", caps)
        if isinstance(best_provider_caps, list):
            matched_caps = list(set(best_provider_caps) & set(caps))
            unmatched_caps = list(set(caps) - set(best_provider_caps))
        else:
            matched_caps = list(caps)
            unmatched_caps = []

        logger.debug(
            "Selected provider '%s' (score=%.2f, %d/%d capabilities matched)",
            best_provider,
            best_score,
            len(matched_caps),
            len(caps),
        )

        return ProviderSelection(
            provider_id=best_provider,
            confidence=best_score,
            matched_capabilities=matched_caps,
            unmatched_capabilities=unmatched_caps,
            estimated_cost=context.metadata.get(f"provider_cost.{best_provider}", 50.0),
            estimated_latency_ms=context.metadata.get(f"provider_latency.{best_provider}", 5000.0),
            reasoning=f"Selected provider '{best_provider}' with score {best_score:.2f} "
                      f"({len(matched_caps)}/{len(caps)} capabilities matched from {len(scored)} candidates)",
        )
