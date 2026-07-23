"""Unit tests for RoutingPolicy."""

from __future__ import annotations

from workflow_orchestrator.decision.decision_models import (
    ApprovalRequirement,
    DecisionContext,
    ExecutionDecision,
    ProjectPhase,
)
from workflow_orchestrator.decision.routing_policy import RoutingPolicy


class TestRoutingPolicy:
    """Tests for the RoutingPolicy."""

    def setup_method(self) -> None:
        self.policy = RoutingPolicy()

    def test_default_policy_name(self) -> None:
        """Test default policy has 'default' name."""
        assert self.policy.config.name == "default"

    def test_cost_optimized_policy(self) -> None:
        """Test cost-optimized policy configuration."""
        policy = RoutingPolicy.cost_optimized()
        assert policy.config.prefer_cost_over_quality
        assert policy.config.max_cost_tier == "medium"

    def test_quality_optimized_policy(self) -> None:
        """Test quality-optimized policy configuration."""
        policy = RoutingPolicy.quality_optimized()
        assert not policy.config.prefer_cost_over_quality
        assert policy.config.min_quality == "stable"
        assert policy.config.max_cost_tier == "premium"

    def test_fast_policy(self) -> None:
        """Test fast policy configuration."""
        policy = RoutingPolicy.fast()
        assert policy.config.prefer_latency_over_quality
        assert policy.config.min_quality == "experimental"

    def test_safe_policy(self) -> None:
        """Test safe policy configuration."""
        policy = RoutingPolicy.safe()
        assert policy.config.require_capability_coverage == 0.9
        assert not policy.config.fallback_enabled
        assert policy.config.human_approval_threshold == 0.6

    def test_set_preferred_provider(self) -> None:
        """Test setting preferred provider."""
        self.policy.set_preferred_provider("my_provider")
        assert self.policy.config.preferred_provider == "my_provider"

    def test_set_preferred_agent(self) -> None:
        """Test setting preferred agent."""
        self.policy.set_preferred_agent("my_agent")
        assert self.policy.config.preferred_agent == "my_agent"

    def test_set_approval_threshold(self) -> None:
        """Test setting approval threshold."""
        self.policy.set_human_approval_threshold(0.5)
        assert self.policy.config.human_approval_threshold == 0.5

    def test_set_approval_threshold_clamped(self) -> None:
        """Test that threshold is clamped to [0, 1]."""
        self.policy.set_human_approval_threshold(-0.5)
        assert self.policy.config.human_approval_threshold == 0.0
        self.policy.set_human_approval_threshold(1.5)
        assert self.policy.config.human_approval_threshold == 1.0

    def test_apply_to_decision_approval_required(self) -> None:
        """Test that approval is required when confidence is below threshold."""
        decision = ExecutionDecision(
            decision_type="route_execution",
        )
        decision.selected_provider.confidence = 0.2
        decision.selected_agent.confidence = 0.2

        policy = RoutingPolicy.safe()  # threshold = 0.6
        context = DecisionContext()

        result = policy.apply_to_decision(decision, context)
        assert result.requires_approval
        assert result.approval_requirement == ApprovalRequirement.REQUIRED

    def test_apply_to_decision_preferred_provider(self) -> None:
        """Test that preferred provider is applied."""
        policy = RoutingPolicy()
        policy.set_preferred_provider("preferred_provider")

        decision = ExecutionDecision()
        context = DecisionContext()

        result = policy.apply_to_decision(decision, context)
        assert result.selected_provider.provider_id == "preferred_provider"

    def test_score_provider_full_coverage(self) -> None:
        """Test scoring a provider with full capability coverage."""
        score = self.policy.score_provider(
            provider_capabilities=["cap_a", "cap_b", "cap_c"],
            required_capabilities=["cap_a", "cap_b"],
            estimated_cost=10.0,
            estimated_latency_ms=100.0,
            quality_score=0.8,
        )
        assert score > 0.5
        assert score <= 1.0

    def test_score_provider_no_coverage(self) -> None:
        """Test scoring a provider with no capability coverage yields low score."""
        score = self.policy.score_provider(
            provider_capabilities=["cap_c", "cap_d"],
            required_capabilities=["cap_a", "cap_b"],
        )
        # Coverage is 0, but quality contribution gives a minimal score
        assert score < 0.3

    def test_score_provider_no_required(self) -> None:
        """Test scoring with empty required capabilities."""
        score = self.policy.score_provider(
            provider_capabilities=[],
            required_capabilities=[],
        )
        assert score == 0.0

    def test_fallback_enabled_default(self) -> None:
        """Test that fallback is enabled by default."""
        assert self.policy.config.fallback_enabled

    def test_apply_to_decision_fallback_config(self) -> None:
        """Test that fallback setting is applied to decision."""
        policy = RoutingPolicy.safe()
        decision = ExecutionDecision()
        context = DecisionContext()

        result = policy.apply_to_decision(decision, context)
        assert not result.fallback_available
