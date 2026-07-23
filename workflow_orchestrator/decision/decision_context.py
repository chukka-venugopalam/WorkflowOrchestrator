"""Decision context assembler — gathers all information needed for decisions.

The Decision Context is built from multiple sources:
- Project state (phase, status)
- Execution state (completed/failed steps, results)
- Registry state (available providers, agents, capabilities)
- User preferences
- Active constraints

It is assembled before any rules are evaluated.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.decision.decision_models import (
    DecisionContext,
    ProjectPhase,
)

logger = logging.getLogger(__name__)


class DecisionContextBuilder:
    """Builds a DecisionContext from available data sources.

    The builder gathers information from the execution engine, state engine,
    capability registry, and user configuration into a single context object
    that the Decision Engine uses to evaluate rules.

    Usage:
        >>> builder = DecisionContextBuilder()
        >>> context = builder.build(
        ...     project_phase="coding",
        ...     execution_status="running",
        ...     completed_steps=["step_1", "step_2"],
        ... )
    """

    def build(
        self,
        project_phase: str | ProjectPhase = ProjectPhase.UNKNOWN,
        execution_status: str = "idle",
        completed_steps: list[str] | None = None,
        failed_steps: list[str] | None = None,
        available_capabilities: list[str] | None = None,
        available_providers: list[str] | None = None,
        available_agents: list[str] | None = None,
        workflow_state: dict[str, Any] | None = None,
        execution_results: dict[str, Any] | None = None,
        errors: list[dict[str, Any]] | None = None,
        user_preferences: dict[str, Any] | None = None,
        constraints: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DecisionContext:
        """Build a DecisionContext from the given data.

        Args:
            project_phase: Current project phase.
            execution_status: Current execution status.
            completed_steps: Steps that have completed.
            failed_steps: Steps that have failed.
            available_capabilities: Capabilities available in the registry.
            available_providers: Providers available in the registry.
            available_agents: Agents available in the registry.
            workflow_state: Current workflow state.
            execution_results: Results from recent step executions.
            errors: Recent errors encountered.
            user_preferences: User-configured preferences.
            constraints: Active constraints.
            metadata: Additional context metadata.

        Returns:
            A fully populated DecisionContext.
        """
        if isinstance(project_phase, str):
            try:
                project_phase = ProjectPhase(project_phase)
            except ValueError:
                project_phase = ProjectPhase.UNKNOWN

        context = DecisionContext(
            project_phase=project_phase,
            execution_status=execution_status,
            completed_steps=completed_steps or [],
            failed_steps=failed_steps or [],
            available_capabilities=available_capabilities or [],
            available_providers=available_providers or [],
            available_agents=available_agents or [],
            workflow_state=workflow_state or {},
            execution_results=execution_results or {},
            errors=errors or [],
            user_preferences=user_preferences or {},
            constraints=constraints or [],
            metadata=metadata or {},
        )

        logger.debug(
            "Built decision context: phase=%s, status=%s, %d providers, %d agents, %d capabilities",
            context.project_phase.value,
            context.execution_status,
            len(context.available_providers),
            len(context.available_agents),
            len(context.available_capabilities),
        )
        return context

    def build_from_workflow_state(
        self,
        workflow_state: dict[str, Any],
        project_phase: ProjectPhase = ProjectPhase.UNKNOWN,
        available_capabilities: list[str] | None = None,
        available_providers: list[str] | None = None,
        available_agents: list[str] | None = None,
        user_preferences: dict[str, Any] | None = None,
    ) -> DecisionContext:
        """Build a DecisionContext from workflow state data.

        Args:
            workflow_state: Dict with keys like ``status``, ``completed_nodes``,
                ``failed_nodes``, ``step_results``.
            project_phase: Current project phase.
            available_capabilities: Available capabilities.
            available_providers: Available providers.
            available_agents: Available agents.
            user_preferences: User preferences.

        Returns:
            A DecisionContext populated from workflow state.
        """
        completed = list(workflow_state.get("completed_nodes", workflow_state.get("completed_steps", [])))
        failed = list(workflow_state.get("failed_nodes", workflow_state.get("failed_steps", [])))
        status = workflow_state.get("status", "idle")
        results = workflow_state.get("step_results", {})

        return self.build(
            project_phase=project_phase,
            execution_status=status,
            completed_steps=[str(s) for s in completed],
            failed_steps=[str(s) for s in failed],
            available_capabilities=available_capabilities,
            available_providers=available_providers,
            available_agents=available_agents,
            workflow_state=workflow_state,
            execution_results=results,
            user_preferences=user_preferences,
        )

    def update_context(
        self,
        context: DecisionContext,
        **updates: Any,
    ) -> DecisionContext:
        """Create an updated copy of a DecisionContext with new values.

        Args:
            context: The original DecisionContext.
            **updates: Fields to update (e.g., ``execution_status="failed"``).

        Returns:
            A new DecisionContext with the updated fields.
        """
        new_context = DecisionContext(
            project_phase=updates.get("project_phase", context.project_phase),
            execution_status=updates.get("execution_status", context.execution_status),
            completed_steps=updates.get("completed_steps", list(context.completed_steps)),
            failed_steps=updates.get("failed_steps", list(context.failed_steps)),
            available_capabilities=updates.get("available_capabilities", list(context.available_capabilities)),
            available_providers=updates.get("available_providers", list(context.available_providers)),
            available_agents=updates.get("available_agents", list(context.available_agents)),
            workflow_state=updates.get("workflow_state", dict(context.workflow_state)),
            execution_results=updates.get("execution_results", dict(context.execution_results)),
            errors=updates.get("errors", list(context.errors)),
            user_preferences=updates.get("user_preferences", dict(context.user_preferences)),
            constraints=updates.get("constraints", list(context.constraints)),
            metadata=updates.get("metadata", dict(context.metadata)),
        )

        if isinstance(new_context.project_phase, str):
            try:
                new_context.project_phase = ProjectPhase(new_context.project_phase)
            except ValueError:
                new_context.project_phase = ProjectPhase.UNKNOWN

        return new_context
