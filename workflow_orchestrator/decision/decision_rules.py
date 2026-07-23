"""Decision rules — rule-based system for planning, fallback, and recovery decisions.

The rules engine evaluates a set of rules against the current DecisionContext
to produce deterministic decisions. Every decision is traceable to an explicit rule.

Rules NEVER perform:
- AI reasoning
- Provider-specific logic
- Subjective judgments
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.decision.decision_models import (
    DecisionContext,
    DecisionRule,
    ExecutionDecision,
    ProjectPhase,
    RuleEvaluationResult,
)

logger = logging.getLogger(__name__)


class DecisionRules:
    """Evaluates decision rules against a DecisionContext.

    Rules are evaluated in priority order. The first rule whose
    condition matches determines the decision. If no rule matches,
    a default "halt" decision is produced.

    Usage:
        >>> rules = DecisionRules()
        >>> result = rules.evaluate(context)
        >>> print(result.decision_type)
        'route_execution'
    """

    def __init__(self) -> None:
        self._rules: list[DecisionRule] = []
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        """Register the built-in default decision rules."""
        self._rules = [
            DecisionRule(
                rule_id="error_recovery",
                name="Error Recovery",
                description="Handle execution errors with appropriate recovery",
                priority=10,
                condition="Any failed steps exist and context has errors",
                action="Select recovery action based on error type",
            ),
            DecisionRule(
                rule_id="route_execution",
                name="Route Execution",
                description="Route execution to the best provider-agent pair",
                priority=20,
                condition="Required capabilities are known and providers/agents are available",
                action="Select best provider and agent for the required capabilities",
            ),
            DecisionRule(
                rule_id="select_capabilities",
                name="Select Capabilities",
                description="Select required capabilities based on project phase and goal",
                priority=30,
                condition="Project phase is known and no capabilities are selected",
                action="Determine which capabilities are needed for the current phase",
            ),
            DecisionRule(
                rule_id="handle_fallback",
                name="Handle Fallback",
                description="Use fallback provider/agent when primary is unavailable",
                priority=40,
                condition="Primary provider or agent failed and fallback is available",
                action="Select alternative provider or agent",
            ),
            DecisionRule(
                rule_id="trigger_approval",
                name="Trigger Approval",
                description="Request human approval for high-risk decisions",
                priority=50,
                condition="Decision confidence is below threshold or action is high-risk",
                action="Pause execution and request human approval",
            ),
            DecisionRule(
                rule_id="skip_step",
                name="Skip Step",
                description="Skip a step when its output is not critical",
                priority=60,
                condition="A non-critical step has failed and on_failure=continue",
                action="Mark step as skipped and continue execution",
            ),
            DecisionRule(
                rule_id="complete_or_halt",
                name="Complete or Halt",
                description="Complete execution or halt on unrecoverable errors",
                priority=100,
                condition="No other rule matched or execution is complete",
                action="Complete if all steps done, otherwise halt with error",
            ),
        ]

    def register_rule(self, rule: DecisionRule) -> None:
        """Register a custom decision rule.

        Args:
            rule: The DecisionRule to register.

        The rule is inserted in priority order.
        """
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority)

    def evaluate(
        self,
        context: DecisionContext,
    ) -> tuple[str, RuleEvaluationResult]:
        """Evaluate the decision rules against a context.

        Rules are evaluated in priority order. Returns the first
        matching rule's result.

        Args:
            context: The decision context to evaluate against.

        Returns:
            Tuple of (decision_type, RuleEvaluationResult).
        """
        evaluated: list[RuleEvaluationResult] = []

        for rule in self._rules:
            result = self._evaluate_rule(rule, context)
            evaluated.append(result)

            if result.matched:
                logger.debug(
                    "Rule '%s' matched: %s (confidence=%.2f)",
                    rule.rule_id,
                    result.suggestion,
                    result.confidence,
                )
                return result.suggestion, result

        # No rule matched — return default halt
        default = RuleEvaluationResult(
            rule=self._rules[-1],
            matched=True,
            confidence=1.0,
            reasoning="No specific rule matched; defaulting to halt",
            suggestion="halt",
        )
        return "halt", default

    def _evaluate_rule(
        self,
        rule: DecisionRule,
        context: DecisionContext,
    ) -> RuleEvaluationResult:
        """Evaluate a single rule against the context.

        Args:
            rule: The rule to evaluate.
            context: The decision context.

        Returns:
            RuleEvaluationResult indicating whether the rule matched.
        """
        rule_id = rule.rule_id

        if rule_id == "error_recovery":
            return self._eval_error_recovery(context)
        elif rule_id == "route_execution":
            return self._eval_route_execution(context)
        elif rule_id == "select_capabilities":
            return self._eval_select_capabilities(context)
        elif rule_id == "handle_fallback":
            return self._eval_handle_fallback(context)
        elif rule_id == "trigger_approval":
            return self._eval_trigger_approval(context)
        elif rule_id == "skip_step":
            return self._eval_skip_step(context)
        elif rule_id == "complete_or_halt":
            return self._eval_complete_or_halt(context)

        return RuleEvaluationResult(
            rule=rule,
            matched=False,
            confidence=0.0,
            reasoning=f"Unknown rule ID: {rule_id}",
            suggestion="",
        )

    # ------------------------------------------------------------------
    # Rule implementations
    # ------------------------------------------------------------------

    def _eval_error_recovery(self, context: DecisionContext) -> RuleEvaluationResult:
        """Evaluate whether error recovery is needed."""
        rule = self._rules[0]
        if context.failed_steps and context.errors:
            # Determine the severity of errors
            max_severity = 0
            for error in context.errors:
                severity = error.get("severity", 0) if isinstance(error, dict) else 0
                max_severity = max(max_severity, severity)

            confidence = min(0.5 + (max_severity * 0.1), 1.0)
            return RuleEvaluationResult(
                rule=rule,
                matched=True,
                confidence=confidence,
                reasoning=f"Error recovery needed: {len(context.failed_steps)} failed step(s), {len(context.errors)} error(s)",
                suggestion="recover_error",
            )

        return RuleEvaluationResult(
            rule=rule,
            matched=False,
            confidence=1.0,
            reasoning="No errors to recover from",
            suggestion="",
        )

    def _eval_route_execution(self, context: DecisionContext) -> RuleEvaluationResult:
        """Evaluate whether execution routing is needed."""
        rule = self._rules[1]

        has_capabilities = len(context.available_capabilities) > 0
        has_providers = len(context.available_providers) > 0
        has_agents = len(context.available_agents) > 0

        if has_capabilities and has_providers:
            confidence = 0.8 if has_agents else 0.5
            return RuleEvaluationResult(
                rule=rule,
                matched=True,
                confidence=confidence,
                reasoning=f"Routing available: {len(context.available_capabilities)} capabilities, "
                          f"{len(context.available_providers)} providers, {len(context.available_agents)} agents",
                suggestion="route_execution",
            )

        return RuleEvaluationResult(
            rule=rule,
            matched=False,
            confidence=1.0,
            reasoning="No capabilities or providers available for routing",
            suggestion="",
        )

    def _eval_select_capabilities(self, context: DecisionContext) -> RuleEvaluationResult:
        """Evaluate whether capabilities need to be selected."""
        rule = self._rules[2]

        if context.project_phase != ProjectPhase.UNKNOWN and not context.available_capabilities:
            return RuleEvaluationResult(
                rule=rule,
                matched=True,
                confidence=0.9,
                reasoning=f"Project phase '{context.project_phase.value}' known, but no capabilities selected",
                suggestion="select_capabilities",
            )

        return RuleEvaluationResult(
            rule=rule,
            matched=False,
            confidence=1.0,
            reasoning="Capabilities already selected or project phase unknown",
            suggestion="",
        )

    def _eval_handle_fallback(self, context: DecisionContext) -> RuleEvaluationResult:
        """Evaluate whether fallback handling is needed."""
        rule = self._rules[3]

        # Fallback needed when we have errors but alternatives exist
        has_errors = len(context.errors) > 0
        has_failed = len(context.failed_steps) > 0
        has_multiple_providers = len(context.available_providers) > 1
        has_multiple_agents = len(context.available_agents) > 1

        if (has_errors or has_failed) and (has_multiple_providers or has_multiple_agents):
            return RuleEvaluationResult(
                rule=rule,
                matched=True,
                confidence=0.7,
                reasoning=f"Fallback available: {len(context.available_providers)} providers, "
                          f"{len(context.available_agents)} agents",
                suggestion="handle_fallback",
            )

        return RuleEvaluationResult(
            rule=rule,
            matched=False,
            confidence=1.0,
            reasoning="No fallback needed or no alternatives available",
            suggestion="",
        )

    def _eval_trigger_approval(self, context: DecisionContext) -> RuleEvaluationResult:
        """Evaluate whether human approval is needed."""
        rule = self._rules[4]

        # Check for high-risk indicators
        risk_score = 0
        if context.execution_status == "failed":
            risk_score += 2
        if len(context.failed_steps) >= 3:
            risk_score += 3
        if context.project_phase in (ProjectPhase.DEPLOYMENT, ProjectPhase.VERIFICATION):
            risk_score += 2
        if len(context.constraints) > 5:
            risk_score += 1

        if risk_score >= 4:
            return RuleEvaluationResult(
                rule=rule,
                matched=True,
                confidence=min(risk_score * 0.15, 1.0),
                reasoning=f"High-risk situation detected (risk score: {risk_score}). "
                          f"Human approval recommended.",
                suggestion="trigger_approval",
            )

        return RuleEvaluationResult(
            rule=rule,
            matched=False,
            confidence=1.0,
            reasoning=f"Risk score ({risk_score}) below approval threshold",
            suggestion="",
        )

    def _eval_skip_step(self, context: DecisionContext) -> RuleEvaluationResult:
        """Evaluate whether a step should be skipped."""
        rule = self._rules[5]

        if context.failed_steps and context.execution_status == "running":
            # Check if non-critical steps failed (heuristic: less than 3 failures)
            if len(context.failed_steps) <= 2:
                return RuleEvaluationResult(
                    rule=rule,
                    matched=True,
                    confidence=0.6,
                    reasoning=f"{len(context.failed_steps)} step(s) failed, may be skippable",
                    suggestion="skip_step",
                )

        return RuleEvaluationResult(
            rule=rule,
            matched=False,
            confidence=1.0,
            reasoning="No skippable steps",
            suggestion="",
        )

    def _eval_complete_or_halt(self, context: DecisionContext) -> RuleEvaluationResult:
        """Evaluate whether to complete or halt."""
        rule = self._rules[6]

        # All steps completed
        total_steps = len(context.completed_steps) + len(context.failed_steps)
        if total_steps > 0 and len(context.failed_steps) == 0:
            return RuleEvaluationResult(
                rule=rule,
                matched=True,
                confidence=1.0,
                reasoning=f"All {total_steps} steps completed successfully",
                suggestion="complete",
            )

        # Fatal condition: more failures than successes
        if len(context.failed_steps) > len(context.completed_steps) and len(context.completed_steps) > 0:
            return RuleEvaluationResult(
                rule=rule,
                matched=True,
                confidence=0.9,
                reasoning=f"More failures ({len(context.failed_steps)}) than successes ({len(context.completed_steps)})",
                suggestion="halt",
            )

        # Default: halt
        return RuleEvaluationResult(
            rule=rule,
            matched=True,
            confidence=1.0,
            reasoning="Default: halting execution",
            suggestion="halt",
        )
