"""Routing policies for provider and agent selection.

Policies define the rules for how routing decisions are made:
- Cost vs. quality tradeoffs
- Preferred providers/agents
- Fallback behavior
- Approval thresholds

Policies are deterministic and rule-based.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.decision.decision_models import (
    ApprovalRequirement,
    DecisionContext,
    ExecutionDecision,
    Priority,
    RoutingPolicyConfig,
)

logger = logging.getLogger(__name__)


class RoutingPolicy:
    """Defines and applies routing policies for provider/agent selection.

    Policies are loaded from configuration or created programmatically.
    They are applied by the Decision Engine when routing execution.

    Usage:
        >>> policy = RoutingPolicy(name="cost-optimized")
        >>> policy.set_prefer_cost_over_quality(True)
        >>> decision = policy.apply_to_decision(decision, context)
    """

    def __init__(self, config: RoutingPolicyConfig | None = None, name: str = "default") -> None:
        """Initialize the routing policy.

        Args:
            config: Optional RoutingPolicyConfig. If None, uses defaults.
            name: Policy name (used when no config provided).
        """
        self._config = config or RoutingPolicyConfig(name=name)

    @property
    def config(self) -> RoutingPolicyConfig:
        """The underlying configuration."""
        return self._config

    @classmethod
    def cost_optimized(cls) -> RoutingPolicy:
        """Create a cost-optimized policy.

        Returns:
            A RoutingPolicy configured to prefer lower cost.
        """
        return cls(RoutingPolicyConfig(
            name="cost-optimized",
            description="Prioritize lower cost over quality",
            prefer_cost_over_quality=True,
            max_cost_tier="medium",
            min_quality="beta",
            human_approval_threshold=0.4,
        ))

    @classmethod
    def quality_optimized(cls) -> RoutingPolicy:
        """Create a quality-optimized policy.

        Returns:
            A RoutingPolicy configured to prefer higher quality.
        """
        return cls(RoutingPolicyConfig(
            name="quality-optimized",
            description="Prioritize higher quality over cost",
            prefer_cost_over_quality=False,
            max_cost_tier="premium",
            min_quality="stable",
            human_approval_threshold=0.3,
        ))

    @classmethod
    def fast(cls) -> RoutingPolicy:
        """Create a latency-optimized policy.

        Returns:
            A RoutingPolicy configured to prefer lower latency.
        """
        return cls(RoutingPolicyConfig(
            name="fast",
            description="Prioritize lower latency",
            prefer_latency_over_quality=True,
            max_cost_tier="high",
            min_quality="experimental",
            human_approval_threshold=0.2,
        ))

    @classmethod
    def safe(cls) -> RoutingPolicy:
        """Create a safe policy with conservative defaults.

        Returns:
            A conservative RoutingPolicy with high approval thresholds.
        """
        return cls(RoutingPolicyConfig(
            name="safe",
            description="Conservative policy with high approval thresholds",
            prefer_cost_over_quality=False,
            max_cost_tier="high",
            min_quality="gold",
            require_capability_coverage=0.9,
            fallback_enabled=False,
            human_approval_threshold=0.6,
        ))

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_prefer_cost_over_quality(self, value: bool) -> None:
        """Set whether to prefer cost over quality.

        Args:
            value: True to prefer lower cost, False to prefer higher quality.
        """
        self._config.prefer_cost_over_quality = value

    def set_prefer_latency_over_quality(self, value: bool) -> None:
        """Set whether to prefer latency over quality.

        Args:
            value: True to prefer lower latency, False to prefer higher quality.
        """
        self._config.prefer_latency_over_quality = value

    def set_preferred_provider(self, provider_id: str) -> None:
        """Set a preferred provider.

        Args:
            provider_id: The provider ID to prefer.
        """
        self._config.preferred_provider = provider_id

    def set_preferred_agent(self, agent_id: str) -> None:
        """Set a preferred agent.

        Args:
            agent_id: The agent ID to prefer.
        """
        self._config.preferred_agent = agent_id

    def set_human_approval_threshold(self, threshold: float) -> None:
        """Set the confidence threshold for human approval.

        Args:
            threshold: Value between 0.0 and 1.0. Lower confidence values
                below this threshold will trigger human approval.
        """
        self._config.human_approval_threshold = max(0.0, min(1.0, threshold))

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------

    def apply_to_decision(
        self,
        decision: ExecutionDecision,
        context: DecisionContext,
    ) -> ExecutionDecision:
        """Apply this policy to an execution decision.

        Modifies the decision based on policy rules:
        - Sets approval requirements based on confidence vs threshold
        - Adjusts provider/agent preferences
        - Configures fallback behavior

        Args:
            decision: The execution decision to apply policy to.
            context: The current decision context.

        Returns:
            The modified ExecutionDecision.
        """
        # 1. Check if human approval is needed
        decision = self._evaluate_approval_requirement(decision, context)

        # 2. Apply provider preference
        if self._config.preferred_provider and not decision.selected_provider.provider_id:
            decision.selected_provider.provider_id = self._config.preferred_provider
            decision.selected_provider.reasoning = f"Preferred by policy '{self._config.name}'"

        # 3. Apply agent preference
        if self._config.preferred_agent and not decision.selected_agent.agent_id:
            decision.selected_agent.agent_id = self._config.preferred_agent
            decision.selected_agent.reasoning = f"Preferred by policy '{self._config.name}'"

        # 4. Set fallback availability
        decision.fallback_available = self._config.fallback_enabled

        return decision

    def _evaluate_approval_requirement(
        self,
        decision: ExecutionDecision,
        context: DecisionContext,
    ) -> ExecutionDecision:
        """Evaluate whether human approval is required.

        Args:
            decision: The execution decision.
            context: The decision context.

        Returns:
            Updated decision with approval information.
        """
        threshold = self._config.human_approval_threshold

        # Check provider confidence
        provider_conf = decision.selected_provider.confidence
        agent_conf = decision.selected_agent.confidence
        min_confidence = min(provider_conf, agent_conf)

        if min_confidence < threshold:
            decision.requires_approval = True
            decision.approval_requirement = ApprovalRequirement.REQUIRED
            decision.approval_reason = (
                f"Decision confidence ({min_confidence:.2f}) is below "
                f"policy threshold ({threshold:.2f}). "
                f"Provider confidence: {provider_conf:.2f}, "
                f"Agent confidence: {agent_conf:.2f}."
            )
        elif min_confidence < threshold + 0.2:
            decision.requires_approval = True
            decision.approval_requirement = ApprovalRequirement.RECOMMENDED
            decision.approval_reason = (
                f"Decision confidence ({min_confidence:.2f}) is near the "
                f"approval threshold ({threshold:.2f}). Approval recommended."
            )

        return decision

    def score_provider(
        self,
        provider_capabilities: list[str],
        required_capabilities: list[str],
        estimated_cost: float = 0.0,
        estimated_latency_ms: float = 0.0,
        quality_score: float = 0.5,
    ) -> float:
        """Score a provider for a given set of required capabilities.

        Args:
            provider_capabilities: Capabilities the provider offers.
            required_capabilities: Capabilities required.
            estimated_cost: Cost estimate.
            estimated_latency_ms: Latency estimate in milliseconds.
            quality_score: Provider quality score (0.0 to 1.0).

        Returns:
            Composite score (higher is better).
        """
        # Coverage score
        if not required_capabilities:
            return 0.0

        required_set = set(required_capabilities)
        provider_set = set(provider_capabilities)
        matched = required_set & provider_set
        coverage = len(matched) / len(required_set)

        # Base score from coverage
        score = coverage * 0.4

        # Quality contribution
        score += quality_score * 0.3

        # Cost contribution (inverted: lower cost = higher score)
        if estimated_cost > 0:
            if self._config.prefer_cost_over_quality:
                cost_score = 1.0 - min(estimated_cost / 100.0, 1.0)
                score += cost_score * 0.2
            else:
                cost_score = 1.0 - min(estimated_cost / 100.0, 1.0)
                score += cost_score * 0.1

        # Latency contribution (inverted: lower latency = higher score)
        if estimated_latency_ms > 0:
            if self._config.prefer_latency_over_quality:
                latency_score = 1.0 - min(estimated_latency_ms / 10000.0, 1.0)
                score += latency_score * 0.2
            else:
                latency_score = 1.0 - min(estimated_latency_ms / 10000.0, 1.0)
                score += latency_score * 0.1

        return min(score, 1.0)
