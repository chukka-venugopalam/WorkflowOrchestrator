"""Data models for the Decision Engine.

All models represent deterministic, rule-based decisions.
No AI reasoning, no provider-specific fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DecisionType(Enum):
    """Type of decision the engine can produce."""

    SELECT_PROVIDER = "select_provider"
    SELECT_AGENT = "select_agent"
    SELECT_WORKFLOW = "select_workflow"
    SELECT_CAPABILITY = "select_capability"
    ROUTE_EXECUTION = "route_execution"
    HANDLE_FALLBACK = "handle_fallback"
    TRIGGER_APPROVAL = "trigger_approval"
    RECOVER_ERROR = "recover_error"
    SKIP_STEP = "skip_step"
    HALT = "halt"


class ProjectPhase(Enum):
    """Determined project phase based on state and goals."""

    DISCOVERY = "discovery"
    PLANNING = "planning"
    CODING = "coding"
    VERIFICATION = "verification"
    DEPLOYMENT = "deployment"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class ApprovalRequirement(Enum):
    """Whether human approval is needed."""

    NOT_REQUIRED = "not_required"
    RECOMMENDED = "recommended"
    REQUIRED = "required"
    URGENT = "urgent"


class Priority(Enum):
    """Priority level for a decision or action."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Decision Context
# ---------------------------------------------------------------------------


@dataclass
class DecisionMetadata:
    """Metadata about a decision for auditing and tracing.

    Attributes:
        decision_id: Unique identifier for this decision.
        decision_type: The type of decision made.
        timestamp: ISO-8601 timestamp of when the decision was made.
        rule_id: The ID of the rule that produced this decision.
        triggered_by: What triggered this decision (e.g., "step.failed").
        trace: Detailed decision trace for debugging.
        priority: Priority of this decision.
    """

    decision_id: str = ""
    decision_type: str = ""
    timestamp: str = ""
    rule_id: str = ""
    triggered_by: str = ""
    trace: list[str] = field(default_factory=list)
    priority: str = "normal"


@dataclass
class DecisionContext:
    """Contextual information for making a decision.

    This is assembled by the Decision Engine before evaluating any rules.
    It contains all the information needed to make a deterministic decision.

    Attributes:
        project_phase: Current project phase.
        execution_status: Current execution status.
        completed_steps: Steps that have completed.
        failed_steps: Steps that have failed.
        available_capabilities: Capabilities available in the registry.
        available_providers: Providers available in the registry.
        available_agents: Agents available in the registry.
        workflow_state: Current workflow state (status, progress).
        execution_results: Results from recent step executions.
        errors: Recent errors encountered.
        user_preferences: User-configured preferences.
        constraints: Active constraints.
        metadata: Additional context metadata.
    """

    project_phase: ProjectPhase = ProjectPhase.UNKNOWN
    execution_status: str = "idle"
    completed_steps: list[str] = field(default_factory=list)
    failed_steps: list[str] = field(default_factory=list)
    available_capabilities: list[str] = field(default_factory=list)
    available_providers: list[str] = field(default_factory=list)
    available_agents: list[str] = field(default_factory=list)
    workflow_state: dict[str, Any] = field(default_factory=dict)
    execution_results: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)
    user_preferences: dict[str, Any] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Decision Rules
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DecisionRule:
    """An immutable decision rule.

    Rules are deterministic: given the same context, the same rule
    always produces the same result.

    Attributes:
        rule_id: Unique rule identifier.
        name: Human-readable rule name.
        description: Description of what this rule does.
        priority: Rule evaluation priority (lower = evaluated first).
        condition: Description of the condition this rule checks.
        action: Description of the action this rule takes.
    """

    rule_id: str
    name: str
    description: str = ""
    priority: int = 100
    condition: str = ""
    action: str = ""


@dataclass
class RuleEvaluationResult:
    """Result of evaluating a decision rule.

    Attributes:
        rule: The rule that was evaluated.
        matched: Whether the rule's condition was met.
        confidence: Confidence in this result (0.0 to 1.0).
        reasoning: Human-readable reasoning.
        suggestion: Suggested action if matched.
    """

    rule: DecisionRule
    matched: bool = False
    confidence: float = 0.0
    reasoning: str = ""
    suggestion: str = ""


# ---------------------------------------------------------------------------
# Routing & Selection
# ---------------------------------------------------------------------------


@dataclass
class RoutingPolicyConfig:
    """Configuration for routing policies.

    Attributes:
        name: Policy name.
        description: Policy description.
        prefer_cost_over_quality: Whether to prioritize cost over quality.
        prefer_latency_over_quality: Whether to prioritize latency over quality.
        max_cost_tier: Maximum acceptable cost tier.
        min_quality: Minimum acceptable quality level.
        preferred_provider: Preferred provider ID (empty = no preference).
        preferred_agent: Preferred agent ID (empty = no preference).
        require_capability_coverage: Minimum fraction of capabilities that must be covered.
        fallback_enabled: Whether automatic fallback is enabled.
        human_approval_threshold: Confidence threshold below which human approval is required.
    """

    name: str = "default"
    description: str = "Default routing policy"
    prefer_cost_over_quality: bool = False
    prefer_latency_over_quality: bool = False
    max_cost_tier: str = "high"
    min_quality: str = "beta"
    preferred_provider: str = ""
    preferred_agent: str = ""
    require_capability_coverage: float = 0.5
    fallback_enabled: bool = True
    human_approval_threshold: float = 0.3


@dataclass
class ProviderSelection:
    """Result of selecting a provider.

    Attributes:
        provider_id: The selected provider ID.
        confidence: Confidence in this selection (0.0 to 1.0).
        matched_capabilities: Capabilities this provider can fulfill.
        unmatched_capabilities: Capabilities this provider cannot fulfill.
        estimated_cost: Estimated cost of using this provider.
        estimated_latency_ms: Estimated latency in milliseconds.
        reasoning: Human-readable reasoning for the selection.
    """

    provider_id: str = ""
    confidence: float = 0.0
    matched_capabilities: list[str] = field(default_factory=list)
    unmatched_capabilities: list[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    estimated_latency_ms: float = 0.0
    reasoning: str = ""


@dataclass
class AgentSelection:
    """Result of selecting an agent.

    Attributes:
        agent_id: The selected agent ID.
        confidence: Confidence in this selection (0.0 to 1.0).
        matched_capabilities: Capabilities this agent can fulfill.
        unmatched_capabilities: Capabilities this agent cannot fulfill.
        reasoning: Human-readable reasoning for the selection.
    """

    agent_id: str = ""
    confidence: float = 0.0
    matched_capabilities: list[str] = field(default_factory=list)
    unmatched_capabilities: list[str] = field(default_factory=list)
    reasoning: str = ""


@dataclass
class WorkflowSelection:
    """Result of selecting a workflow.

    Attributes:
        workflow_name: Name of the selected workflow.
        workflow_source: Source file or definition.
        confidence: Confidence in this selection (0.0 to 1.0).
        required_capabilities: Capabilities this workflow requires.
        reasoning: Human-readable reasoning.
    """

    workflow_name: str = ""
    workflow_source: str = ""
    confidence: float = 0.0
    required_capabilities: list[str] = field(default_factory=list)
    reasoning: str = ""


# ---------------------------------------------------------------------------
# Execution Decision
# ---------------------------------------------------------------------------


@dataclass
class ExecutionDecision:
    """A complete decision produced by the Decision Engine.

    Attributes:
        decision_type: What kind of decision this is.
        metadata: Decision metadata for auditing.
        should_proceed: Whether execution should proceed.
        selected_provider: Provider selection result (if applicable).
        selected_agent: Agent selection result (if applicable).
        selected_workflow: Workflow selection result (if applicable).
        required_capabilities: Capabilities required for the next step.
        requires_approval: Whether human approval is needed.
        approval_reason: Why human approval is required/recommended.
        fallback_available: Whether a fallback option exists.
        fallback_decision: The fallback decision (if applicable).
        reasoning: Complete human-readable reasoning.
    """

    decision_type: str = ""
    metadata: DecisionMetadata = field(default_factory=DecisionMetadata)
    should_proceed: bool = True
    selected_provider: ProviderSelection = field(default_factory=ProviderSelection)
    selected_agent: AgentSelection = field(default_factory=AgentSelection)
    selected_workflow: WorkflowSelection = field(default_factory=WorkflowSelection)
    required_capabilities: list[str] = field(default_factory=list)
    requires_approval: bool = False
    approval_reason: str = ""
    approval_requirement: ApprovalRequirement = ApprovalRequirement.NOT_REQUIRED
    fallback_available: bool = False
    fallback_decision: Optional[ExecutionDecision] = None
    reasoning: str = ""


# ---------------------------------------------------------------------------
# Recovery Decisions
# ---------------------------------------------------------------------------


@dataclass
class RecoveryAction:
    """An action to recover from an error.

    Attributes:
        action_type: Type of recovery action (retry, fallback, escalate, halt).
        description: Human-readable description of the recovery action.
        target_provider: Provider to use for fallback (if applicable).
        target_agent: Agent to use for fallback (if applicable).
        max_retries: Maximum retries (if action is retry).
        delay_seconds: Delay before retry.
        escalate_to_human: Whether this must be escalated to a human.
        reasoning: Why this recovery action was chosen.
    """

    action_type: str = "retry"
    description: str = ""
    target_provider: str = ""
    target_agent: str = ""
    max_retries: int = 3
    delay_seconds: float = 1.0
    escalate_to_human: bool = False
    reasoning: str = ""
