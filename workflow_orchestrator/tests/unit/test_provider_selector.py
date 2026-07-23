"""Unit tests for ProviderSelector."""

from __future__ import annotations

from workflow_orchestrator.decision.decision_models import DecisionContext
from workflow_orchestrator.decision.provider_selector import ProviderSelector


class TestProviderSelector:
    """Tests for the ProviderSelector."""

    def setup_method(self) -> None:
        self.selector = ProviderSelector()

    def test_select_no_providers(self) -> None:
        """Test selection with no available providers."""
        context = DecisionContext()
        selection = self.selector.select(context)
        assert selection.provider_id == ""
        assert "No providers" in selection.reasoning

    def test_select_first_provider_no_caps(self) -> None:
        """Test selection with no capabilities required."""
        context = DecisionContext(
            available_providers=["provider_a", "provider_b"],
        )
        selection = self.selector.select(context)
        assert selection.provider_id == "provider_a"
        assert selection.confidence > 0

    def test_select_with_capabilities(self) -> None:
        """Test selection with capabilities using metadata."""
        context = DecisionContext(
            available_providers=["provider_a", "provider_b"],
            available_capabilities=["cap_1", "cap_2"],
            metadata={
                "provider_capabilities.provider_a": ["cap_1", "cap_2"],
                "provider_capabilities.provider_b": ["cap_1"],
                "provider_quality.provider_a": 0.9,
                "provider_quality.provider_b": 0.7,
            },
        )
        selection = self.selector.select(
            context,
            required_capabilities=["cap_1", "cap_2"],
        )
        assert selection.provider_id == "provider_a"
        assert "cap_1" in selection.matched_capabilities
        assert "cap_2" in selection.matched_capabilities

    def test_select_exclude_providers(self) -> None:
        """Test selection with excluded providers."""
        context = DecisionContext(
            available_providers=["provider_a", "provider_b", "provider_c"],
            metadata={
                "provider_capabilities.provider_a": ["cap_1"],
                "provider_capabilities.provider_b": ["cap_1"],
                "provider_capabilities.provider_c": ["cap_1"],
            },
        )
        selection = self.selector.select(
            context,
            required_capabilities=["cap_1"],
            exclude_providers=["provider_a"],
        )
        assert selection.provider_id != "provider_a"

    def test_select_all_excluded(self) -> None:
        """Test selection when all providers are excluded."""
        context = DecisionContext(
            available_providers=["provider_a", "provider_b"],
        )
        selection = self.selector.select(
            context,
            exclude_providers=["provider_a", "provider_b"],
        )
        assert selection.provider_id == ""

    def test_select_with_metadata(self) -> None:
        """Test selection with quality and cost metadata."""
        context = DecisionContext(
            available_providers=["fast_provider", "cheap_provider"],
            available_capabilities=["cap_1"],
            metadata={
                "provider_capabilities.fast_provider": ["cap_1"],
                "provider_capabilities.cheap_provider": ["cap_1"],
                "provider_quality.fast_provider": 0.9,
                "provider_quality.cheap_provider": 0.5,
                "provider_cost.fast_provider": 80.0,
                "provider_cost.cheap_provider": 10.0,
                "provider_latency.fast_provider": 500.0,
                "provider_latency.cheap_provider": 3000.0,
            },
        )
        selection = self.selector.select(context, required_capabilities=["cap_1"])
        assert selection.provider_id is not None
        assert selection.confidence > 0
