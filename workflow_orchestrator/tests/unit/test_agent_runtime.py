"""Unit tests for Agent Runtime and agent implementations."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from workflow_orchestrator.intelligence.models import (
    AgentManifest,
    AgentStatus,
    Capability,
    ExecutionRequest,
    ExecutionResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_agent():
    """Create a mock agent for testing."""
    agent = MagicMock()
    agent.agent_id = "test-agent"
    agent.agent_name = "Test Agent"

    manifest = AgentManifest(
        id="test-agent",
        name="Test Agent",
        version="1.0.0",
        capabilities=[
            Capability(id="codegen.general", description="Code gen"),
        ],
    )
    agent.manifest.return_value = manifest
    agent.launch = AsyncMock()
    agent.shutdown = AsyncMock()
    agent.execute = AsyncMock(return_value=ExecutionResult(
        task_id="test-task",
        success=True,
        output="Test output",
    ))
    agent.cancel = AsyncMock()
    agent.resume = AsyncMock()
    agent.heartbeat = AsyncMock(return_value=AgentStatus.IDLE)
    return agent


@pytest.fixture
def mock_execution_request():
    """Create a mock execution request."""
    return ExecutionRequest(
        task_id="test-task",
        goal="Build a feature",
        temperature=0.7,
        max_tokens=4096,
    )


# ---------------------------------------------------------------------------
# Agent Registry tests
# ---------------------------------------------------------------------------


class TestAgentRegistry:
    """Tests for AgentRegistry."""

    def test_register_and_lookup(self, mock_agent):
        """Test registering and looking up an agent."""
        from workflow_orchestrator.intelligence.agent_registry import AgentRegistry

        registry = AgentRegistry()
        registry.register(mock_agent)

        agent = registry.lookup("test-agent")
        assert agent is not None
        assert agent.agent_id == "test-agent"

    def test_register_duplicate_raises(self, mock_agent):
        """Test registering a duplicate agent raises."""
        from workflow_orchestrator.intelligence.agent_registry import AgentRegistry

        registry = AgentRegistry()
        registry.register(mock_agent)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(mock_agent)

    def test_register_overwrite(self, mock_agent):
        """Test overwriting an agent registration."""
        from workflow_orchestrator.intelligence.agent_registry import AgentRegistry

        registry = AgentRegistry()
        registry.register(mock_agent)

        # Should not raise with overwrite=True
        registry.register(mock_agent, overwrite=True)

    def test_unregister(self, mock_agent):
        """Test unregistering an agent."""
        from workflow_orchestrator.intelligence.agent_registry import AgentRegistry

        registry = AgentRegistry()
        registry.register(mock_agent)
        result = registry.unregister("test-agent")

        assert result is True
        assert registry.lookup("test-agent") is None

    def test_list_agents(self, mock_agent):
        """Test listing all agents."""
        from workflow_orchestrator.intelligence.agent_registry import AgentRegistry

        registry = AgentRegistry()
        registry.register(mock_agent)

        agents = registry.list_agents()
        assert len(agents) == 1

    def test_find_by_capability(self, mock_agent):
        """Test finding agents by capability."""
        from workflow_orchestrator.intelligence.agent_registry import AgentRegistry

        registry = AgentRegistry()
        registry.register(mock_agent)

        agents = registry.find_by_capability("codegen.general")
        assert len(agents) == 1

        agents = registry.find_by_capability("nonexistent")
        assert len(agents) == 0


# ---------------------------------------------------------------------------
# Agent Runtime tests
# ---------------------------------------------------------------------------


class TestAgentRuntime:
    """Tests for AgentRuntime."""

    @pytest.mark.asyncio
    async def test_launch(self, mock_agent):
        """Test launching an agent."""
        from workflow_orchestrator.intelligence.agent_registry import AgentRegistry
        from workflow_orchestrator.runtime import AgentRuntime

        registry = AgentRegistry()
        registry.register(mock_agent)

        runtime = AgentRuntime(agent_registry=registry)
        success = await runtime.launch("test-agent")

        assert success is True
        assert mock_agent.launch.called

    @pytest.mark.asyncio
    async def test_launch_not_found(self):
        """Test launching an unregistered agent."""
        from workflow_orchestrator.intelligence.agent_registry import AgentRegistry
        from workflow_orchestrator.runtime import AgentRuntime

        registry = AgentRegistry()
        runtime = AgentRuntime(agent_registry=registry)

        success = await runtime.launch("nonexistent")
        assert success is False

    @pytest.mark.asyncio
    async def test_execute(self, mock_agent, mock_execution_request):
        """Test executing a task through an agent."""
        from workflow_orchestrator.intelligence.agent_registry import AgentRegistry
        from workflow_orchestrator.runtime import AgentRuntime

        registry = AgentRegistry()
        registry.register(mock_agent)

        runtime = AgentRuntime(agent_registry=registry)
        result = await runtime.execute("test-agent", mock_execution_request)

        assert result.success is True
        assert result.task_id == "test-task"

    @pytest.mark.asyncio
    async def test_execute_not_found(self, mock_execution_request):
        """Test execution with unregistered agent."""
        from workflow_orchestrator.intelligence.agent_registry import AgentRegistry
        from workflow_orchestrator.runtime import AgentRuntime

        registry = AgentRegistry()
        runtime = AgentRuntime(agent_registry=registry)

        result = await runtime.execute("nonexistent", mock_execution_request)
        assert result.success is False
        assert "not found" in result.error_message

    @pytest.mark.asyncio
    async def test_shutdown(self, mock_agent):
        """Test shutting down an agent."""
        from workflow_orchestrator.intelligence.agent_registry import AgentRegistry
        from workflow_orchestrator.runtime import AgentRuntime

        registry = AgentRegistry()
        registry.register(mock_agent)

        runtime = AgentRuntime(agent_registry=registry)
        await runtime.launch("test-agent")
        success = await runtime.shutdown("test-agent")

        assert success is True
        assert mock_agent.shutdown.called

    @pytest.mark.asyncio
    async def test_cancel(self, mock_agent):
        """Test cancelling an agent task."""
        from workflow_orchestrator.intelligence.agent_registry import AgentRegistry
        from workflow_orchestrator.runtime import AgentRuntime

        registry = AgentRegistry()
        registry.register(mock_agent)

        runtime = AgentRuntime(agent_registry=registry)
        await runtime.cancel("test-agent", "task-123")

        assert mock_agent.cancel.called

    @pytest.mark.asyncio
    async def test_heartbeat(self, mock_agent):
        """Test agent heartbeat."""
        from workflow_orchestrator.intelligence.agent_registry import AgentRegistry
        from workflow_orchestrator.runtime import AgentRuntime

        registry = AgentRegistry()
        registry.register(mock_agent)

        runtime = AgentRuntime(agent_registry=registry)
        status = await runtime.heartbeat("test-agent")

        assert status == AgentStatus.IDLE


# ---------------------------------------------------------------------------
# Base Agent tests
# ---------------------------------------------------------------------------


class TestBaseAgent:
    """Tests for BaseAgent."""

    @pytest.mark.asyncio
    async def test_launch_and_shutdown(self):
        """Test agent launch and shutdown."""
        from workflow_orchestrator.intelligence.models import AgentManifest
        from workflow_orchestrator.agents.base import BaseAgent

        class TestAgent(BaseAgent):
            def manifest(self):
                return AgentManifest(
                    id="test.agent",
                    name="Test Agent",
                )

        agent = TestAgent()
        await agent.launch()
        await agent.shutdown()
        # Should not raise

    @pytest.mark.asyncio
    async def test_execute_before_launch_raises(self):
        """Test that execute before launch raises."""
        from workflow_orchestrator.intelligence.models import AgentManifest
        from workflow_orchestrator.agents.base import BaseAgent

        class TestAgent(BaseAgent):
            def manifest(self):
                return AgentManifest(
                    id="test.agent",
                    name="Test Agent",
                )

        agent = TestAgent()
        with pytest.raises(RuntimeError, match="not launched"):
            await agent.execute(MagicMock())

    def test_create_workspace(self, tmp_path):
        """Test creating a workspace."""
        from workflow_orchestrator.intelligence.models import AgentManifest
        from workflow_orchestrator.agents.base import BaseAgent

        class TestAgent(BaseAgent):
            def manifest(self):
                return AgentManifest(
                    id="test.agent",
                    name="Test Agent",
                )

        agent = TestAgent(workspace_base=str(tmp_path))
        workspace = agent.create_workspace("test-ws")

        assert workspace.exists()
        assert "test-ws" in str(workspace)

    def test_cleanup_workspace(self, tmp_path):
        """Test cleaning up a workspace."""
        from workflow_orchestrator.intelligence.models import AgentManifest
        from workflow_orchestrator.agents.base import BaseAgent

        class TestAgent(BaseAgent):
            def manifest(self):
                return AgentManifest(
                    id="test.agent",
                    name="Test Agent",
                )

        agent = TestAgent(workspace_base=str(tmp_path))
        agent.create_workspace("test-ws")
        agent.cleanup_workspace()

        assert agent.get_workspace() is None
