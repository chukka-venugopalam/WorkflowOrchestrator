"""Registry for coding agent adapters.

Manages registration, lifecycle, status tracking, and capability
discovery for all coding agents. No agent implementations exist
in this module — it only manages the registry layer.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.intelligence.agent import IAgent
from workflow_orchestrator.intelligence.models import (
    AgentManifest,
    AgentStatus,
    Capability,
)

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry that manages available coding agents.

    Supports:
    - Register and unregister agent adapters
    - Look up agents by ID or capability
    - Track agent status
    - Discover agent capabilities

    Usage:
        >>> registry = AgentRegistry()
        >>> registry.register(agent_instance)
        >>> agent = registry.lookup("claude-code")
        >>> agents = registry.find_by_capability("codegen.nextjs")
    """

    def __init__(self) -> None:
        self._agents: dict[str, IAgent] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, agent: IAgent, overwrite: bool = False) -> None:
        """Register an agent adapter.

        Args:
            agent: An IAgent implementation.
            overwrite: If True, replace an existing agent with the same ID.

        Raises:
            ValueError: If an agent with the same ID is already registered
                and ``overwrite`` is False.
        """
        manifest = agent.manifest()
        aid = manifest.id

        if aid in self._agents and not overwrite:
            raise ValueError(
                f"Agent '{aid}' is already registered. "
                "Use overwrite=True to replace."
            )

        self._agents[aid] = agent
        logger.info(
            "Registered agent '%s' (v%s) with %d capabilities",
            aid,
            manifest.version,
            len(manifest.capabilities),
        )

    def unregister(self, agent_id: str) -> bool:
        """Unregister an agent.

        Args:
            agent_id: The agent identifier.

        Returns:
            True if the agent was unregistered, False if not found.
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info("Unregistered agent '%s'", agent_id)
            return True
        return False

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def lookup(self, agent_id: str) -> IAgent | None:
        """Look up an agent by ID.

        Args:
            agent_id: The agent identifier.

        Returns:
            The agent instance, or None if not found.
        """
        return self._agents.get(agent_id)

    def lookup_required(self, agent_id: str) -> IAgent:
        """Look up an agent by ID, raising if not found.

        Args:
            agent_id: The agent identifier.

        Returns:
            The agent instance.

        Raises:
            KeyError: If the agent is not registered.
        """
        agent = self.lookup(agent_id)
        if agent is None:
            raise KeyError(
                f"Agent '{agent_id}' is not registered. "
                f"Available: {list(self._agents.keys())}"
            )
        return agent

    def list_agents(self) -> list[IAgent]:
        """List all registered agents.

        Returns:
            List of all IAgent instances.
        """
        return list(self._agents.values())

    def list_ids(self) -> list[str]:
        """List all registered agent IDs.

        Returns:
            Sorted list of agent IDs.
        """
        return sorted(self._agents.keys())

    # ------------------------------------------------------------------
    # Capability-based discovery
    # ------------------------------------------------------------------

    def find_by_capability(self, capability_id: str) -> list[IAgent]:
        """Find agents that support a specific capability.

        Args:
            capability_id: The capability ID to search for.

        Returns:
            List of agents that declare support for this capability.
        """
        results: list[IAgent] = []
        for agent in self._agents.values():
            manifest = agent.manifest()
            for cap in manifest.capabilities:
                if cap.id == capability_id:
                    results.append(agent)
                    break
        return results

    def find_by_capabilities(
        self,
        capability_ids: list[str],
        require_all: bool = False,
    ) -> list[IAgent]:
        """Find agents that support one or more capabilities.

        Args:
            capability_ids: List of capability IDs to search for.
            require_all: If True, agent must support ALL capabilities.

        Returns:
            List of matching agents.
        """
        if require_all:
            return [
                a for a in self._agents.values()
                if self._supports_all(a, capability_ids)
            ]
        return [
            a for a in self._agents.values()
            if self._supports_any(a, capability_ids)
        ]

    def _supports_all(self, agent: IAgent, cap_ids: list[str]) -> bool:
        """Check if an agent supports all given capabilities."""
        agent_caps = {c.id for c in agent.manifest().capabilities}
        return all(cid in agent_caps for cid in cap_ids)

    def _supports_any(self, agent: IAgent, cap_ids: list[str]) -> bool:
        """Check if an agent supports any of the given capabilities."""
        agent_caps = {c.id for c in agent.manifest().capabilities}
        return any(cid in agent_caps for cid in cap_ids)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def metadata(self, agent_id: str) -> AgentManifest | None:
        """Get the manifest for an agent.

        Args:
            agent_id: The agent identifier.

        Returns:
            AgentManifest, or None if not found.
        """
        agent = self.lookup(agent_id)
        if agent is None:
            return None
        return agent.manifest()

    def capabilities(self, agent_id: str) -> list[Capability]:
        """Get the capabilities of a specific agent.

        Args:
            agent_id: The agent identifier.

        Returns:
            List of Capability objects, or empty list if agent not found.
        """
        agent = self.lookup(agent_id)
        if agent is None:
            return []
        return agent.manifest().capabilities

    def all_capabilities(self) -> dict[str, list[Capability]]:
        """Get capabilities for all agents.

        Returns:
            Dict mapping agent ID to list of capabilities.
        """
        return {aid: a.manifest().capabilities for aid, a in self._agents.items()}

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    async def get_status(self, agent_id: str) -> AgentStatus | None:
        """Get the current status of an agent.

        Args:
            agent_id: The agent identifier.

        Returns:
            AgentStatus, or None if agent not found.
        """
        agent = self.lookup(agent_id)
        if agent is None:
            return None
        try:
            return await agent.heartbeat("_status_")
        except Exception:
            return AgentStatus.FAILED

    # ------------------------------------------------------------------
    # Count
    # ------------------------------------------------------------------

    @property
    def count(self) -> int:
        """Number of registered agents."""
        return len(self._agents)
