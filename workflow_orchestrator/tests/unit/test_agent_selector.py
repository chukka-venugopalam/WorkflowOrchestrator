"""Unit tests for AgentSelector."""

from __future__ import annotations

from workflow_orchestrator.decision.agent_selector import AgentSelector
from workflow_orchestrator.decision.decision_models import DecisionContext


class TestAgentSelector:
    """Tests for the AgentSelector."""

    def setup_method(self) -> None:
        self.selector = AgentSelector()

    def test_select_no_agents(self) -> None:
        """Test selection with no available agents."""
        context = DecisionContext()
        selection = self.selector.select(context)
        assert selection.agent_id == ""
        assert "No agents" in selection.reasoning

    def test_select_first_agent(self) -> None:
        """Test selection picks first agent with no specific caps."""
        context = DecisionContext(
            available_agents=["agent_a", "agent_b"],
        )
        selection = self.selector.select(context)
        assert selection.agent_id == "agent_a"

    def test_select_with_capabilities(self) -> None:
        """Test selection with capability metadata."""
        context = DecisionContext(
            available_agents=["agent_a", "agent_b"],
            available_capabilities=["cap_1", "cap_2"],
            metadata={
                "agent_capabilities.agent_a": ["cap_1", "cap_2"],
                "agent_capabilities.agent_b": ["cap_1"],
            },
        )
        selection = self.selector.select(
            context,
            required_capabilities=["cap_1", "cap_2"],
        )
        assert selection.agent_id == "agent_a"
        assert "cap_2" in selection.matched_capabilities

    def test_select_with_preferred_provider(self) -> None:
        """Test selection with preferred provider compatibility."""
        context = DecisionContext(
            available_agents=["agent_a", "agent_b"],
            available_capabilities=["cap_1"],
            metadata={
                "agent_capabilities.agent_a": ["cap_1"],
                "agent_capabilities.agent_b": ["cap_1"],
                "agent_providers.agent_a": ["provider_x"],
                "agent_providers.agent_b": ["provider_y"],
            },
        )
        selection = self.selector.select(
            context,
            required_capabilities=["cap_1"],
            preferred_provider="provider_x",
        )
        assert selection.agent_id == "agent_a"

    def test_select_exclude_agents(self) -> None:
        """Test selection with excluded agents."""
        context = DecisionContext(
            available_agents=["agent_a", "agent_b"],
            metadata={
                "agent_capabilities.agent_a": ["cap_1"],
                "agent_capabilities.agent_b": ["cap_1"],
            },
        )
        selection = self.selector.select(
            context,
            required_capabilities=["cap_1"],
            exclude_agents=["agent_a"],
        )
        assert selection.agent_id != "agent_a"

    def test_select_with_preferences(self) -> None:
        """Test selection with user preferences."""
        context = DecisionContext(
            available_agents=["agent_a", "agent_b"],
            metadata={
                "agent_capabilities.agent_a": ["cap_1"],
                "agent_capabilities.agent_b": ["cap_1"],
            },
            user_preferences={"preferred_agents": ["agent_b"]},
        )
        selection = self.selector.select(
            context,
            required_capabilities=["cap_1"],
        )
        assert selection.agent_id == "agent_b"

    def test_select_all_excluded(self) -> None:
        """Test selection when all agents are excluded."""
        context = DecisionContext(
            available_agents=["agent_a"],
        )
        selection = self.selector.select(
            context,
            exclude_agents=["agent_a"],
        )
        assert selection.agent_id == ""
