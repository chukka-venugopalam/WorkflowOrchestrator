"""Unit tests for the Router."""

from __future__ import annotations

import pytest
from workflow_orchestrator.intelligence.router import Router
from workflow_orchestrator.intelligence.capability_matcher import CapabilityMatcher
from workflow_orchestrator.intelligence.provider_registry import ProviderRegistry
from workflow_orchestrator.intelligence.agent_registry import AgentRegistry
from tests.fixtures.intelligence_mocks import MockProvider, MockAgent


class TestRouter:
    def setup_method(self) -> None:
        self.provider_registry = ProviderRegistry()
        self.agent_registry = AgentRegistry()

        self.provider_registry.register(MockProvider("p1", ["cap.a", "cap.b"]))
        self.provider_registry.register(MockProvider("p2", ["cap.b", "cap.c"]))
        self.provider_registry.register(MockProvider("p3", ["cap.a"]))

        self.agent_registry.register(MockAgent("a1", ["cap.a", "cap.b"]))
        self.agent_registry.register(MockAgent("a2", ["cap.b", "cap.c"]))
        self.agent_registry.register(MockAgent("a3", ["cap.a"]))

        self.matcher = CapabilityMatcher(self.provider_registry, self.agent_registry)
        self.router = Router(self.matcher)

    async def test_route_basic(self) -> None:
        decision = await self.router.route(["cap.a"])
        assert decision.selected_provider_id != ""
        assert decision.selected_agent_id != ""
        assert decision.confidence > 0
        assert len(decision.trace) > 0

    def test_route_sync_wrapper(self) -> None:
        """Test routing using asyncio.run."""
        import asyncio
        decision = asyncio.run(self.router.route(["cap.a"]))
        assert decision.selected_provider_id != ""

    def test_route_with_preferred_provider(self) -> None:
        import asyncio
        decision = asyncio.run(self.router.route(["cap.a"], preferred_provider="p3"))
        assert decision.selected_provider_id == "p3"

    def test_route_with_preferred_agent(self) -> None:
        import asyncio
        decision = asyncio.run(self.router.route(["cap.b"], preferred_agent="a2"))
        assert decision.selected_agent_id == "a2"

    def test_route_no_match(self) -> None:
        import asyncio
        decision = asyncio.run(self.router.route(["nonexistent.cap"]))
        assert decision.selected_provider_id == ""
        assert decision.selected_agent_id == ""
        assert decision.confidence == 0.0

    def test_fallback_routing(self) -> None:
        import asyncio
        # First route with all providers
        original = asyncio.run(self.router.route(["cap.a"]))
        assert original.selected_provider_id != ""

        # Fallback excluding the selected provider
        fallback = asyncio.run(self.router.route_fallback(
            original,
            exclude_providers=[original.selected_provider_id],
        ))

        if fallback.selected_provider_id:
            assert fallback.selected_provider_id != original.selected_provider_id

    def test_fallback_no_alternatives(self) -> None:
        import asyncio
        # Route for cap.c which only p2-a2 can handle
        decision = asyncio.run(self.router.route(["cap.c"]))

        # Exclude the only provider-agent that can handle it
        fallback = asyncio.run(self.router.route_fallback(
            decision,
            exclude_providers=[decision.selected_provider_id],
            exclude_agents=[decision.selected_agent_id],
        ))
        assert fallback.selected_provider_id == ""
        assert fallback.selected_agent_id == ""

    def test_batch_routing(self) -> None:
        import asyncio
        decisions = asyncio.run(self.router.route_batch([
            ["cap.a"],
            ["cap.b"],
            ["cap.c"],
        ]))
        assert len(decisions) == 3
        for d in decisions:
            assert d.selected_provider_id != ""
