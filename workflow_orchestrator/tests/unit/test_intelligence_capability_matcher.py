"""Unit tests for the CapabilityMatcher."""

from __future__ import annotations

import pytest
from workflow_orchestrator.intelligence.capability_matcher import CapabilityMatcher, MatchResult
from workflow_orchestrator.intelligence.models import (
    Capability,
    CostEstimate,
    ExecutionRequest,
    ExecutionResult,
    ProviderHealth,
    ProviderManifest,
    ProviderStatus,
    AgentManifest,
    AgentStatus,
)
from workflow_orchestrator.intelligence.provider_registry import ProviderRegistry
from workflow_orchestrator.intelligence.agent_registry import AgentRegistry
from tests.fixtures.intelligence_mocks import MockProvider, MockAgent


class TestCapabilityMatcher:
    def setup_method(self) -> None:
        self.provider_registry = ProviderRegistry()
        self.agent_registry = AgentRegistry()

        # Register providers
        self.provider_registry.register(MockProvider("p1", ["cap.a", "cap.b"]))
        self.provider_registry.register(MockProvider("p2", ["cap.b", "cap.c"]))

        # Register agents
        self.agent_registry.register(MockAgent("a1", ["cap.a", "cap.b"]))
        self.agent_registry.register(MockAgent("a2", ["cap.b", "cap.c"]))

        self.matcher = CapabilityMatcher(self.provider_registry, self.agent_registry)

    def test_match_single_capability(self) -> None:
        result = self.matcher.match(["cap.a"])
        assert len(result.candidates) > 0
        # p1-a1 should match cap.a
        matching = [c for c in result.candidates if c.provider_id == "p1" and c.agent_id == "a1"]
        assert len(matching) == 1

    def test_match_all_capabilities(self) -> None:
        result = self.matcher.match(["cap.a", "cap.b", "cap.c"])
        assert len(result.candidates) > 0

    def test_match_no_matching_provider(self) -> None:
        result = self.matcher.match(["nonexistent.cap"])
        assert len(result.candidates) == 0
        assert "nonexistent.cap" in result.unmatched_capabilities

    def test_match_unmatched_capabilities(self) -> None:
        result = self.matcher.match(["cap.a", "nonexistent.cap"])
        assert "nonexistent.cap" in result.unmatched_capabilities

    def test_match_empty_requirements(self) -> None:
        result = self.matcher.match([])
        assert len(result.candidates) == 0
        assert len(result.unmatched_capabilities) == 0

    def test_candidates_are_sorted_by_score(self) -> None:
        result = self.matcher.match(["cap.a", "cap.b"])
        if len(result.candidates) >= 2:
            scores = [c.score for c in result.candidates]
            assert scores == sorted(scores, reverse=True)

    def test_min_coverage_filter(self) -> None:
        result = self.matcher.match(["cap.a", "cap.b", "cap.c", "cap.d"], min_coverage=0.75)
        # Only cap.a, cap.b, cap.c exist, so coverage for p2-a2 is 2/4 = 0.5 < 0.75
        for c in result.candidates:
            assert c.score >= 0.75

    def test_find_providers_for_capability(self) -> None:
        providers = self.matcher.find_providers_for_capability("cap.a")
        assert "p1" in providers
        assert "p2" not in providers

    def test_find_agents_for_capability(self) -> None:
        agents = self.matcher.find_agents_for_capability("cap.c")
        assert "a2" in agents
        assert "a1" not in agents

    def test_coverage_report(self) -> None:
        report = self.matcher.coverage_report()
        assert report["total_capabilities"] >= 3
        assert report["total_providers"] == 2
        assert report["total_agents"] == 2
