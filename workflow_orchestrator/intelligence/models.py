"""Data models for the Intelligence Plane.

Defines all dataclasses used by providers, agents, sessions,
routing, prompt assembly, and context budgeting.

All models are provider-agnostic — no vendor-specific fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ProviderStatus(Enum):
    """Lifecycle status of a provider."""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    DEPRECATED = "deprecated"
    SHUTDOWN = "shutdown"


class AgentStatus(Enum):
    """Lifecycle status of an agent."""

    IDLE = "idle"
    LAUNCHING = "launching"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionErrorType(Enum):
    """Typed errors for provider/agent execution."""

    TRANSIENT = "transient"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    AUTHENTICATION = "authentication"
    INVALID_REQUEST = "invalid_request"
    CAPABILITY_NOT_SUPPORTED = "capability_not_supported"
    INTERNAL_ERROR = "internal_error"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class SessionState(Enum):
    """State of a session."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Capability models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Capability:
    """A declarable capability identifier.

    Attributes:
        id: Namespaced capability ID (e.g., ``reasoning.code-review``).
        version: Optional version string for the capability.
        description: Human-readable description.
    """

    id: str
    version: str = "1.0.0"
    description: str = ""

    def __post_init__(self) -> None:
        if "." not in self.id:
            raise ValueError(f"Capability ID must be namespaced: '{self.id}'")


# ---------------------------------------------------------------------------
# Provider models
# ---------------------------------------------------------------------------


@dataclass
class ProviderManifest:
    """Declared metadata about a provider.

    Attributes:
        id: Unique provider identifier (e.g., ``anthropic.claude``).
        name: Human-readable provider name.
        version: Provider version string.
        description: Description of the provider.
        capabilities: Capabilities this provider offers.
        cost_model: Description of pricing model.
        rate_limits: Declared rate limits as key-value pairs.
        context_window: Maximum context size (in abstract units).
        deprecated: Whether this provider version is deprecated.
        metadata: Additional provider-specific metadata.
    """

    id: str
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    capabilities: list[Capability] = field(default_factory=list)
    cost_model: str = ""
    rate_limits: dict[str, Any] = field(default_factory=dict)
    context_window: int = 0
    deprecated: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderHealth:
    """Health status of a provider at a point in time.

    Attributes:
        provider_id: The provider identifier.
        status: Current health status.
        latency_ms: Average response latency in milliseconds.
        error_rate: Recent error rate (0.0 to 1.0).
        last_checked: ISO-8601 timestamp of last health check.
        message: Human-readable status message.
    """

    provider_id: str
    status: ProviderStatus = ProviderStatus.UNINITIALIZED
    latency_ms: float = 0.0
    error_rate: float = 0.0
    last_checked: str = ""
    message: str = ""


@dataclass
class CostEstimate:
    """Estimated cost of a provider invocation.

    Attributes:
        provider_id: The provider identifier.
        estimated_cost: Estimated cost in abstract units.
        currency: Currency or unit label.
        confidence: Confidence in the estimate (0.0 to 1.0).
        breakdown: Optional cost breakdown by component.
    """

    provider_id: str
    estimated_cost: float = 0.0
    currency: str = "credits"
    confidence: float = 0.5
    breakdown: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent models
# ---------------------------------------------------------------------------


@dataclass
class AgentManifest:
    """Declared metadata about an agent.

    Attributes:
        id: Unique agent identifier (e.g., ``claude-code``).
        name: Human-readable agent name.
        version: Agent version string.
        description: Description of the agent.
        capabilities: Capabilities this agent supports.
        requires_local_runtime: Whether the agent needs local execution.
        supports_parallel_tasks: Whether the agent can run parallel tasks.
        sandbox_requirements: Sandbox isolation requirements.
        metadata: Additional agent-specific metadata.
    """

    id: str
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    capabilities: list[Capability] = field(default_factory=list)
    requires_local_runtime: bool = True
    supports_parallel_tasks: bool = False
    sandbox_requirements: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Execution models
# ---------------------------------------------------------------------------


@dataclass
class ArtifactReference:
    """Reference to an artifact produced or consumed during execution.

    Attributes:
        artifact_id: Unique artifact identifier.
        name: Human-readable name for the artifact.
        content_type: MIME type or content category.
        size_bytes: Size in bytes (0 if unknown).
        hash: Content hash for integrity verification.
        uri: URI to access the artifact content.
        metadata: Additional artifact metadata.
    """

    artifact_id: str = ""
    name: str = ""
    content_type: str = "application/octet-stream"
    size_bytes: int = 0
    hash: str = ""
    uri: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionRequest:
    """A request to execute a task through a provider or agent.

    Attributes:
        task_id: Unique task identifier.
        capability: The capability being requested.
        goal: The goal or objective for this execution.
        context: Contextual information for execution.
        artifacts: Artifacts to include.
        constraints: Execution constraints.
        max_tokens: Maximum output size.
        temperature: Creativity/randomness parameter.
        timeout_seconds: Maximum execution time.
        metadata: Additional request metadata.
    """

    task_id: str = ""
    capability: Capability | None = None
    goal: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    artifacts: list[ArtifactReference] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout_seconds: int = 120
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of a provider or agent execution.

    Attributes:
        task_id: The task that was executed.
        success: Whether execution succeeded.
        status: Final execution status.
        output: Primary output content.
        artifacts: Artifacts produced during execution.
        error_type: Typed error if execution failed.
        error_message: Human-readable error message.
        duration_ms: Execution duration in milliseconds.
        cost: Estimated cost of this execution.
        token_usage: Token usage breakdown (abstract units).
        metadata: Additional result metadata.
    """

    task_id: str
    success: bool = False
    status: ProviderStatus | AgentStatus = ProviderStatus.UNINITIALIZED
    output: str = ""
    artifacts: list[ArtifactReference] = field(default_factory=list)
    error_type: ExecutionErrorType | None = None
    error_message: str = ""
    duration_ms: float = 0.0
    cost: CostEstimate | None = None
    token_usage: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Session models
# ---------------------------------------------------------------------------


@dataclass
class TaskRecord:
    """Record of a single task executed within a session.

    Attributes:
        task_id: Unique task identifier.
        capability_id: The capability used for this task.
        provider_id: The provider that executed this task.
        agent_id: The agent that executed this task.
        goal: The task goal.
        status: Execution status.
        started_at: ISO-8601 timestamp.
        completed_at: ISO-8601 timestamp.
        duration_ms: Execution duration.
        result: The execution result.
        artifacts: Artifacts produced.
    """

    task_id: str
    capability_id: str = ""
    provider_id: str = ""
    agent_id: str = ""
    goal: str = ""
    status: str = "pending"
    started_at: str = ""
    completed_at: str = ""
    duration_ms: float = 0.0
    result: ExecutionResult | None = None
    artifacts: list[ArtifactReference] = field(default_factory=list)


@dataclass
class Session:
    """A session tracking a unit of work across providers and agents.

    Attributes:
        session_id: Unique session identifier.
        project: Project name or identifier.
        workflow: Workflow name or identifier.
        provider_id: Currently active provider.
        agent_id: Currently active agent.
        state: Current session state.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last update timestamp.
        completed_at: ISO-8601 completion timestamp.
        task_history: History of tasks executed in this session.
        artifacts: Artifacts accumulated during the session.
        metadata: Additional session metadata.
    """

    session_id: str
    project: str = ""
    workflow: str = ""
    provider_id: str = ""
    agent_id: str = ""
    state: SessionState = SessionState.ACTIVE
    created_at: str = ""
    updated_at: str = ""
    completed_at: str = ""
    task_history: list[TaskRecord] = field(default_factory=list)
    artifacts: list[ArtifactReference] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Prompt models
# ---------------------------------------------------------------------------


@dataclass
class Prompt:
    """A structured prompt ready for provider formatting.

    Attributes:
        goal: The primary objective.
        context: Contextual information (truncated for budget).
        artifacts: Referenced artifacts.
        constraints: Explicit constraints.
        history: Prior conversation or execution history.
        budget: Context budget summary.
        metadata: Additional prompt metadata.
    """

    goal: str = ""
    context: str = ""
    artifacts: list[ArtifactReference] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)
    budget: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextBundle:
    """Provider-agnostic intermediate representation of context.

    This is the cross-provider communication format — all providers
    receive this and format it according to their own conventions.

    Attributes:
        immutable_core: The project contract summary (never summarized).
        working_set: Relevant files/artifacts from dependency steps.
        rolling_summary: Compressed summary of prior step outputs.
        recent_history: Recent turn history.
        budget_remaining: Remaining budget after assembly.
    """

    immutable_core: str = ""
    working_set: list[ArtifactReference] = field(default_factory=list)
    rolling_summary: str = ""
    recent_history: list[dict[str, Any]] = field(default_factory=list)
    budget_remaining: int = 0


# ---------------------------------------------------------------------------
# Routing models
# ---------------------------------------------------------------------------


@dataclass
class RoutingDecision:
    """Result of routing a capability requirement to a provider and agent.

    Attributes:
        required_capabilities: The capabilities that were required.
        selected_provider_id: The chosen provider.
        selected_agent_id: The chosen agent.
        confidence: Confidence in this routing decision (0.0 to 1.0).
        alternatives: Alternative routing options.
        reasoning: Human-readable reasoning for the decision.
        trace: Detailed routing trace for debugging.
    """

    required_capabilities: list[str] = field(default_factory=list)
    selected_provider_id: str = ""
    selected_agent_id: str = ""
    confidence: float = 0.0
    alternatives: list[dict[str, Any]] = field(default_factory=list)
    reasoning: str = ""
    trace: list[str] = field(default_factory=list)


@dataclass
class RoutingCandidate:
    """A candidate provider-agent pair for routing.

    Attributes:
        provider_id: The provider identifier.
        agent_id: The agent identifier.
        matched_capabilities: Capabilities this pair can fulfill.
        score: Composite match score (higher is better).
        estimated_cost: Estimated cost estimate.
        estimated_latency_ms: Estimated latency in milliseconds.
    """

    provider_id: str
    agent_id: str
    matched_capabilities: list[str] = field(default_factory=list)
    score: float = 0.0
    estimated_cost: float = 0.0
    estimated_latency_ms: float = 0.0


# ---------------------------------------------------------------------------
# Context Budget models
# ---------------------------------------------------------------------------


@dataclass
class BudgetAllocation:
    """Allocation of context budget across layers.

    Attributes:
        layer_name: Name of the context layer.
        allocated: Allocated budget units.
        used: Used budget units.
        priority: Priority level (0=highest).
        compression_ratio: Applied compression ratio.
        summary: Summary of this layer's content.
    """

    layer_name: str
    allocated: int = 0
    used: int = 0
    priority: int = 0
    compression_ratio: float = 1.0
    summary: str = ""


# ---------------------------------------------------------------------------
# Planner models
# ---------------------------------------------------------------------------


@dataclass
class Plan:
    """A plan produced by the planner.

    Attributes:
        goal: The original goal this plan addresses.
        steps: Ordered list of step descriptions.
        required_capabilities: Capabilities needed to execute.
        estimated_steps: Estimated number of steps.
        metadata: Additional plan metadata.
    """

    goal: str = ""
    steps: list[str] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)
    estimated_steps: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
