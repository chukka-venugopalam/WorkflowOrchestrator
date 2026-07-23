"""Decision Engine — orchestrates rule-based decisions for workflow execution.

The Decision Engine determines WHAT should happen next by:
1. Analyzing goals to determine required capabilities
2. Determining the current project phase
3. Selecting the best provider/agent for required capabilities
4. Finding the best workflow for the goal
5. Evaluating rules for error recovery and fallback
6. Applying routing policies
7. Triggering human approval when needed

It NEVER performs AI reasoning.
It NEVER knows provider names (Claude, ChatGPT, Gemini, etc.).
It only reasons using capabilities, project state, and configuration.

Every decision is:
- Deterministic (same inputs → same outputs)
- Traceable to an explicit rule
- Provider-agnostic
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from workflow_orchestrator.decision.agent_selector import AgentSelector
from workflow_orchestrator.decision.decision_context import DecisionContextBuilder
from workflow_orchestrator.decision.decision_models import (
    ApprovalRequirement,
    DecisionContext,
    DecisionMetadata,
    ExecutionDecision,
    ProjectPhase,
)
from workflow_orchestrator.decision.decision_rules import DecisionRules
from workflow_orchestrator.decision.goal_analyzer import GoalAnalyzer
from workflow_orchestrator.decision.phase_manager import PhaseManager
from workflow_orchestrator.decision.provider_selector import ProviderSelector
from workflow_orchestrator.decision.routing_policy import RoutingPolicy
from workflow_orchestrator.decision.workflow_selector import WorkflowSelector

logger = logging.getLogger(__name__)


class DecisionEngine:
    """Orchestrates all decision components for deterministic decision making.

    The Decision Engine is the single entry point for all routing and
    planning decisions. It coordinates the selectors, analyzers, rules,
    and policies to produce deterministic, traceable decisions.

    Usage:
        >>> engine = DecisionEngine()
        >>> decision = engine.decide_next_step(
        ...     goal="build and test the api",
        ...     context=context,
        ... )
        >>> print(decision.decision_type)
        'route_execution'
        >>> print(decision.selected_provider.provider_id)
        'anthropic.claude'
    """

    def __init__(
        self,
        goal_analyzer: GoalAnalyzer | None = None,
        phase_manager: PhaseManager | None = None,
        provider_selector: ProviderSelector | None = None,
        agent_selector: AgentSelector | None = None,
        workflow_selector: WorkflowSelector | None = None,
        decision_rules: DecisionRules | None = None,
        routing_policy: RoutingPolicy | None = None,
        context_builder: DecisionContextBuilder | None = None,
    ) -> None:
        """Initialize the Decision Engine with its components.

        All components are optional — defaults are created if not provided.
        This allows for dependency injection of custom implementations.
        """
        self._goal_analyzer = goal_analyzer or GoalAnalyzer()
        self._phase_manager = phase_manager or PhaseManager()
        self._provider_selector = provider_selector or ProviderSelector()
        self._agent_selector = agent_selector or AgentSelector()
        self._workflow_selector = workflow_selector or WorkflowSelector()
        self._decision_rules = decision_rules or DecisionRules()
        self._routing_policy = routing_policy or RoutingPolicy()
        self._context_builder = context_builder or DecisionContextBuilder()

    @property
    def routing_policy(self) -> RoutingPolicy:
        """The routing policy being used."""
        return self._routing_policy

    @property
    def goal_analyzer(self) -> GoalAnalyzer:
        """The goal analyzer."""
        return self._goal_analyzer

    # ------------------------------------------------------------------
    # Main decision entry point
    # ------------------------------------------------------------------

    def decide_next_step(
        self,
        goal: str = "",
        context: DecisionContext | None = None,
        execution_state: dict[str, Any] | None = None,
        user_preferences: dict[str, Any] | None = None,
    ) -> ExecutionDecision:
        """Make a decision about what to do next.

        This is the primary entry point for the Decision Engine.
        It coordinates all sub-components to produce a single decision.

        Args:
            goal: The user's goal or objective.
            context: Optional pre-built DecisionContext.
            execution_state: Optional execution state dict (used to build context).
            user_preferences: Optional user preferences.

        Returns:
            An ExecutionDecision with all selection results and reasoning.
        """
        # Phase 1: Build or use provided context
        if context is None:
            phase = self._phase_manager.determine_phase(
                goal=goal,
                context=None,
            )
            context = self._context_builder.build(
                project_phase=phase,
                execution_status=execution_state.get("status", "idle") if execution_state else "idle",
                completed_steps=list(execution_state.get("completed_nodes", execution_state.get("completed_steps", []))) if execution_state else [],
                failed_steps=list(execution_state.get("failed_nodes", execution_state.get("failed_steps", []))) if execution_state else [],
                user_preferences=user_preferences,
            )

        # Phase 2: Analyze goal for capabilities
        required_capabilities = self._goal_analyzer.analyze(goal, context)

        # Phase 3: Determine project phase (if not already set)
        if context.project_phase == ProjectPhase.UNKNOWN and goal:
            phase = self._phase_manager.determine_phase(goal=goal, context=context)
            context = self._context_builder.update_context(context, project_phase=phase)

        # Phase 4: Select provider
        provider_selection = self._provider_selector.select(
            context=context,
            required_capabilities=required_capabilities,
        )

        # Phase 5: Select agent
        agent_selection = self._agent_selector.select(
            context=context,
            required_capabilities=required_capabilities,
            preferred_provider=provider_selection.provider_id if provider_selection.provider_id else None,
        )

        # Phase 6: Select workflow (if goal is provided)
        workflow_selection = self._workflow_selector.select_for_goal(goal, context) if goal else None

        # Phase 7: Build initial decision
        decision = ExecutionDecision(
            decision_type="route_execution",
            metadata=DecisionMetadata(
                decision_id=uuid.uuid4().hex[:12],
                decision_type="route_execution",
                timestamp=datetime.now(timezone.utc).isoformat(),
                triggered_by="decision_engine.decide_next_step",
                trace=[
                    f"Goal: {goal[:80] if goal else '(none)'}",
                    f"Phase: {context.project_phase.value}",
                    f"Required capabilities: {required_capabilities}",
                ],
            ),
            should_proceed=True,
            selected_provider=provider_selection,
            selected_agent=agent_selection,
            selected_workflow=workflow_selection or None,
            required_capabilities=required_capabilities,
            reasoning=self._build_reasoning(
                context, required_capabilities, provider_selection, agent_selection,
            ),
        )

        # Phase 8: Apply routing policy
        decision = self._routing_policy.apply_to_decision(decision, context)

        # Phase 9: Evaluate decision rules
        decision_type, rule_result = self._decision_rules.evaluate(context)
        decision.decision_type = decision_type
        decision.metadata.rule_id = rule_result.rule.rule_id
        decision.metadata.trace.append(f"Rule '{rule_result.rule.rule_id}' → {decision_type}")
        decision.reasoning += f"\nRule evaluation: {rule_result.reasoning}"

        return decision

    # ------------------------------------------------------------------
    # Specialized decisions
    # ------------------------------------------------------------------

    def decide_recovery(
        self,
        error: dict[str, Any],
        context: DecisionContext,
    ) -> ExecutionDecision:
        """Make a decision about how to recover from an error.

        Args:
            error: The error details (type, message, severity, step).
            context: The current decision context.

        Returns:
            An ExecutionDecision with the recovery plan.
        """
        # Update context with the error
        updated_context = self._context_builder.update_context(
            context,
            errors=context.errors + [error],
        )

        # Evaluate recovery rules
        decision_type, rule_result = self._decision_rules.evaluate(updated_context)

        # Determine if recovery is possible
        can_recover = decision_type in ("recover_error", "handle_fallback", "skip_step")
        needs_approval = decision_type == "trigger_approval"

        return ExecutionDecision(
            decision_type=decision_type,
            metadata=DecisionMetadata(
                decision_id=uuid.uuid4().hex[:12],
                decision_type=decision_type,
                timestamp=datetime.now(timezone.utc).isoformat(),
                triggered_by=f"error: {error.get('type', 'unknown')}",
                rule_id=rule_result.rule.rule_id,
                trace=[
                    f"Error type: {error.get('type', 'unknown')}",
                    f"Error message: {error.get('message', error.get('error', ''))[:100]}",
                    f"Affected step: {error.get('step', 'unknown')}",
                    f"Rule matched: {rule_result.rule.rule_id}",
                    f"Decision: {decision_type}",
                ],
            ),
            should_proceed=can_recover and not needs_approval,
            requires_approval=needs_approval,
            approval_requirement=ApprovalRequirement.REQUIRED if needs_approval else ApprovalRequirement.NOT_REQUIRED,
            approval_reason=f"Error recovery decision '{decision_type}' requires approval" if needs_approval else "",
            reasoning=f"Recovery decision: {decision_type}. {rule_result.reasoning}",
        )

    def decide_workflow(
        self,
        goal: str,
        context: DecisionContext | None = None,
    ) -> ExecutionDecision:
        """Make a decision about which workflow to run.

        Args:
            goal: The user's goal.
            context: Optional decision context.

        Returns:
            An ExecutionDecision with the workflow selection.
        """
        if context is None:
            context = self._context_builder.build()

        workflow_selection = self._workflow_selector.select_for_goal(goal, context)

        return ExecutionDecision(
            decision_type="select_workflow",
            metadata=DecisionMetadata(
                decision_id=uuid.uuid4().hex[:12],
                decision_type="select_workflow",
                timestamp=datetime.now(timezone.utc).isoformat(),
                triggered_by="decision_engine.decide_workflow",
                trace=[f"Goal: {goal[:80]}", f"Workflow: {workflow_selection.workflow_name or '(none)'}"],
            ),
            should_proceed=bool(workflow_selection.workflow_name),
            selected_workflow=workflow_selection,
            required_capabilities=workflow_selection.required_capabilities,
            reasoning=f"Workflow selection: {'found' if workflow_selection.workflow_name else 'not found'}. "
                      f"{workflow_selection.reasoning}",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_reasoning(
        self,
        context: DecisionContext,
        capabilities: list[str],
        provider_selection: object,
        agent_selection: object,
    ) -> str:
        """Build human-readable reasoning for a decision.

        Args:
            context: The decision context.
            capabilities: Required capabilities.
            provider_selection: Provider selection result.
            agent_selection: Agent selection result.

        Returns:
            A human-readable reasoning string.
        """
        parts: list[str] = []

        parts.append(f"Phase: {context.project_phase.value}")
        parts.append(f"Status: {context.execution_status}")
        parts.append(f"Capabilities needed: {len(capabilities)}")

        if hasattr(provider_selection, 'provider_id') and provider_selection.provider_id:
            parts.append(f"Provider: {provider_selection.provider_id}")
        else:
            parts.append("Provider: none")

        if hasattr(agent_selection, 'agent_id') and agent_selection.agent_id:
            parts.append(f"Agent: {agent_selection.agent_id}")
        else:
            parts.append("Agent: none")

        parts.append(f"Steps completed: {len(context.completed_steps)}")
        parts.append(f"Steps failed: {len(context.failed_steps)}")

        return " | ".join(parts)
