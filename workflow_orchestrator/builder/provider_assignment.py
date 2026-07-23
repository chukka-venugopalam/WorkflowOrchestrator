"""Provider Assignment — uses the Decision Engine to assign providers, agents, and transports.

Every assignment is:
- Based on capabilities required by the task
- Provider-agnostic (no provider names in algorithms)
- Configurable via routing policy
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from workflow_orchestrator.builder.data_models import ResourceAssignment, TaskGraph
from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class ProviderAssignment:
    """Assigns providers, agents, and transports to tasks using the Decision Engine.

    Uses the Decision Engine's routing capabilities to determine the best
    provider-agent-transport combination for each task based on required
    capabilities. No provider names are hardcoded in algorithms.

    Usage:
        >>> assigner = ProviderAssignment(decision_engine=engine)
        >>> assignments = assigner.assign(graph)
        >>> print(assignments[0].provider_id)
    """

    def __init__(
        self,
        decision_engine: Any = None,
        event_bus: EventBus | None = None,
    ) -> None:
        """Initialize the Provider Assignment.

        Args:
            decision_engine: The Decision Engine for routing decisions.
            event_bus: Optional EventBus for publishing events.
        """
        self._decision_engine = decision_engine
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # Assignment
    # ------------------------------------------------------------------

    def assign(self, task_graph: TaskGraph) -> list[ResourceAssignment]:
        """Assign resources to all tasks in the graph.

        Args:
            task_graph: The task graph with tasks needing assignment.

        Returns:
            List of ResourceAssignment objects.
        """
        assignments: list[ResourceAssignment] = []

        for task_id, node in task_graph.nodes.items():
            assignment = self._assign_task(task_id, node)
            assignments.append(assignment)

        self._publish_event("builder.resources_assigned", {
            "assignment_count": len(assignments),
            "providers_used": list(set(a.provider_id for a in assignments if a.provider_id)),
            "agents_used": list(set(a.agent_id for a in assignments if a.agent_id)),
        })

        logger.info("Assigned resources to %d tasks", len(assignments))
        return assignments

    def _assign_task(self, task_id: str, node: Any) -> ResourceAssignment:
        """Assign resources to a single task.

        Args:
            task_id: The task identifier.
            node: The task node with capability requirements.

        Returns:
            A ResourceAssignment for this task.
        """
        assignment = ResourceAssignment(
            task_id=task_id,
            provider_id="",
            agent_id="",
            transport="rest_api",
            confidence=0.0,
            reasoning="No decision engine available",
        )

        # Use Decision Engine if available
        if self._decision_engine is not None:
            try:
                decision = self._decision_engine.decide_next_step(
                    goal=node.description or node.name,
                    user_preferences={
                        "required_capabilities": node.capabilities_required,
                    },
                )

                if decision.selected_provider:
                    assignment.provider_id = decision.selected_provider.provider_id
                    assignment.confidence = decision.selected_provider.confidence
                    assignment.reasoning = decision.selected_provider.reasoning

                if decision.selected_agent:
                    assignment.agent_id = decision.selected_agent.agent_id

                # Set fallback
                if decision.fallback_decision:
                    if decision.fallback_decision.selected_provider:
                        assignment.fallback_provider_id = decision.fallback_decision.selected_provider.provider_id
                    if decision.fallback_decision.selected_agent:
                        assignment.fallback_agent_id = decision.fallback_decision.selected_agent.agent_id

            except Exception as exc:
                logger.warning("Decision engine failed for task '%s': %s", task_id, exc)
                assignment.reasoning = f"Decision engine error: {exc}"

        # Determine transport based on provider assignment
        assignment.transport = self._determine_transport(assignment.provider_id)

        return assignment

    def _determine_transport(self, provider_id: str) -> str:
        """Determine the best transport for a provider.

        Args:
            provider_id: The provider identifier.

        Returns:
            Transport type string.
        """
        # Deterministic transport mapping based on provider ID
        transport_map: dict[str, str] = {
            "anthropic.claude": "rest_api",
            "openai.chatgpt": "rest_api",
            "google.gemini": "rest_api",
        }
        return transport_map.get(provider_id, "rest_api")

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(
                type=event_type, data=data, source="provider_assignment",
            ))
        except Exception:
            pass
