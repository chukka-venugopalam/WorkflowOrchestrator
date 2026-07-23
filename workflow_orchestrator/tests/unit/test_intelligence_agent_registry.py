"""Unit tests for the AgentRegistry."""

from __future__ import annotations

import pytest
from workflow_orchestrator.intelligence.agent_registry import AgentRegistry
from workflow_orchestrator.intelligence.models import (
    AgentManifest,
    AgentStatus,
    Capability,
    ExecutionRequest,
    ExecutionResult,
)
from tests.fixtures.intelligence_mocks import MockAgent


class TestAgentRegistry:
    def setup_method(self) -> None:
        self.registry = AgentRegistry()
        self.agent1 = MockAgent("agent.a", ["cap.a", "cap.b"])
        self.agent2 = MockAgent("agent.b", ["cap.b", "cap.c"])

    def test_register_and_lookup(self) -> None:
        self.registry.register(self.agent1)
        assert self.registry.lookup("agent.a") is self.agent1

    def test_register_duplicate_raises(self) -> None:
        self.registry.register(self.agent1)
        with pytest.raises(ValueError, match="already registered"):
            self.registry.register(self.agent1)

    def test_register_overwrite(self) -> None:
        self.registry.register(self.agent1)
        new_agent = MockAgent("agent.a", ["cap.z"])
        self.registry.register(new_agent, overwrite=True)
        assert self.registry.lookup("agent.a") is new_agent

    def test_unregister(self) -> None:
        self.registry.register(self.agent1)
        assert self.registry.unregister("agent.a")
        assert self.registry.lookup("agent.a") is None

    def test_unregister_nonexistent(self) -> None:
        assert not self.registry.unregister("nonexistent")

    def test_lookup_required_found(self) -> None:
        self.registry.register(self.agent1)
        assert self.registry.lookup_required("agent.a") is self.agent1

    def test_lookup_required_not_found(self) -> None:
        with pytest.raises(KeyError):
            self.registry.lookup_required("nonexistent")

    def test_list_agents(self) -> None:
        self.registry.register(self.agent1)
        self.registry.register(self.agent2)
        assert len(self.registry.list_agents()) == 2

    def test_list_ids(self) -> None:
        self.registry.register(self.agent2)
        self.registry.register(self.agent1)
        assert self.registry.list_ids() == ["agent.a", "agent.b"]

    def test_find_by_capability(self) -> None:
        self.registry.register(self.agent1)
        self.registry.register(self.agent2)
        results = self.registry.find_by_capability("cap.a")
        assert len(results) == 1
        assert results[0].manifest().id == "agent.a"

        results = self.registry.find_by_capability("cap.b")
        assert len(results) == 2

    def test_find_by_capabilities_any(self) -> None:
        self.registry.register(self.agent1)
        self.registry.register(self.agent2)
        results = self.registry.find_by_capabilities(["cap.a"])
        assert len(results) == 1

    def test_find_by_capabilities_all(self) -> None:
        self.registry.register(self.agent1)
        self.registry.register(self.agent2)
        results = self.registry.find_by_capabilities(["cap.b"], require_all=True)
        assert len(results) == 2

    def test_metadata(self) -> None:
        self.registry.register(self.agent1)
        manifest = self.registry.metadata("agent.a")
        assert manifest is not None
        assert manifest.id == "agent.a"

    def test_capabilities(self) -> None:
        self.registry.register(self.agent1)
        caps = self.registry.capabilities("agent.a")
        assert len(caps) == 2

    def test_all_capabilities(self) -> None:
        self.registry.register(self.agent1)
        self.registry.register(self.agent2)
        all_caps = self.registry.all_capabilities()
        assert len(all_caps) == 2

    def test_count(self) -> None:
        assert self.registry.count == 0
        self.registry.register(self.agent1)
        assert self.registry.count == 1
