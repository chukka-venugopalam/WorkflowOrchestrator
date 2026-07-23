"""Shared data models for the Autonomous Project Builder.

Defines all dataclasses used across the builder package.
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


class ProjectType(Enum):
    """Type of project being built."""

    WEB = "web"
    MOBILE = "mobile"
    DESKTOP = "desktop"
    CLI = "cli"
    AI = "ai"
    ML = "ml"
    EMBEDDED = "embedded"
    ROBOTICS = "robotics"
    RESEARCH = "research"
    EDUCATION = "education"
    ENTERPRISE = "enterprise"
    HYBRID = "hybrid"
    GAME = "game"
    API = "api"
    LIBRARY = "library"
    INFRASTRUCTURE = "infrastructure"
    UNKNOWN = "unknown"


class ProjectPhase(Enum):
    """Phase of the project lifecycle."""

    INITIALIZING = "initializing"
    CLASSIFYING = "classifying"
    REQUIREMENTS = "requirements"
    ARCHITECTURE = "architecture"
    PLANNING = "planning"
    TASK_CREATION = "task_creation"
    WORKFLOW_GENERATION = "workflow_generation"
    PROVIDER_ASSIGNMENT = "provider_assignment"
    EXECUTION_PLANNING = "execution_planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    DOCUMENTING = "documenting"
    DEPLOYING = "deploying"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatus(Enum):
    """Status of a task in the task graph."""

    PENDING = "pending"
    BLOCKED = "blocked"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


class TaskPriority(Enum):
    """Priority of a task."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VerificationScope(Enum):
    """Scope of verification to run."""

    TASK = "task"
    PHASE = "phase"
    PROJECT = "project"


class CheckpointType(Enum):
    """Type of checkpoint."""

    AUTOMATIC = "automatic"
    MANUAL = "manual"
    PHASE = "phase"
    MILESTONE = "milestone"
    APPROVAL_GATE = "approval_gate"


class RollbackScope(Enum):
    """Scope of a rollback operation."""

    TASK = "task"
    PHASE = "phase"
    PROJECT = "project"


# ---------------------------------------------------------------------------
# Builder configuration
# ---------------------------------------------------------------------------


@dataclass
class BuilderConfig:
    """Configuration for the Project Builder.

    Attributes:
        project_root: Root directory for created projects.
        state_dir: Directory for builder state persistence.
        workflows_dir: Directory for generated workflow YAML files.
        artifacts_dir: Directory for generated artifacts.
        docs_dir: Directory for generated documentation.
        max_concurrent_tasks: Maximum parallel execution tasks.
        auto_verify: Whether to automatically verify after each task.
        auto_deploy: Whether to automatically generate deployment plans.
        auto_document: Whether to automatically generate documentation.
        approval_required_for: List of task names that require human approval.
        checkpoint_frequency: Create checkpoint every N tasks.
        default_retry_policy: Default retry config for tasks.
    """

    project_root: str = ""
    state_dir: str = ".builder"
    workflows_dir: str = "workflows"
    artifacts_dir: str = "artifacts"
    docs_dir: str = "docs"
    max_concurrent_tasks: int = 3
    auto_verify: bool = True
    auto_deploy: bool = True
    auto_document: bool = True
    approval_required_for: list[str] = field(default_factory=list)
    checkpoint_frequency: int = 5
    default_retry_policy: dict[str, Any] = field(default_factory=lambda: {
        "max_retries": 2,
        "delay": 2.0,
        "backoff": 2.0,
    })


# ---------------------------------------------------------------------------
# Project state
# ---------------------------------------------------------------------------


@dataclass
class PhaseState:
    """State of a single project phase.

    Attributes:
        phase: The phase identifier.
        status: Current phase status.
        started_at: ISO-8601 timestamp.
        completed_at: ISO-8601 timestamp.
        completed_tasks: Task IDs completed in this phase.
        failed_tasks: Task IDs that failed in this phase.
        artifacts: Artifact IDs produced in this phase.
        metadata: Additional phase metadata.
    """

    phase: str = ""
    status: str = "pending"
    started_at: str = ""
    completed_at: str = ""
    completed_tasks: list[str] = field(default_factory=list)
    failed_tasks: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectState:
    """Complete state of a builder project.

    Attributes:
        project_id: Unique project identifier.
        project_name: Human-readable project name.
        project_type: Classified project type.
        status: Current project status.
        current_phase: Currently active phase.
        phases: Map of phase name to PhaseState.
        completed_phases: Ordered list of completed phase names.
        failed_phases: List of failed phase names.
        started_at: ISO-8601 timestamp.
        updated_at: ISO-8601 timestamp.
        completed_at: ISO-8601 timestamp.
        metadata: Additional project metadata.
    """

    project_id: str = ""
    project_name: str = ""
    project_type: str = ""
    status: str = "initializing"
    current_phase: str = ""
    phases: dict[str, PhaseState] = field(default_factory=dict)
    completed_phases: list[str] = field(default_factory=list)
    failed_phases: list[str] = field(default_factory=list)
    started_at: str = ""
    updated_at: str = ""
    completed_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Task graph
# ---------------------------------------------------------------------------


@dataclass
class TaskNode:
    """A single node in the task dependency graph.

    Attributes:
        task_id: Unique task identifier.
        name: Human-readable task name.
        description: Task description.
        phase: The phase this task belongs to.
        priority: Task priority.
        status: Current task status.
        dependencies: Task IDs this task depends on.
        capabilities_required: Capabilities needed to execute this task.
        expected_outputs: List of expected output artifact names.
        acceptance_criteria: Criteria for task completion.
        retry_policy: Retry configuration for this task.
        metadata: Additional task metadata.
    """

    task_id: str = ""
    name: str = ""
    description: str = ""
    phase: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    dependencies: list[str] = field(default_factory=list)
    capabilities_required: list[str] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    retry_policy: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "phase": self.phase,
            "priority": self.priority.value,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "capabilities_required": self.capabilities_required,
            "expected_outputs": self.expected_outputs,
            "acceptance_criteria": self.acceptance_criteria,
            "retry_policy": self.retry_policy,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskNode:
        """Create from a dictionary."""
        priority = TaskPriority.MEDIUM
        try:
            priority = TaskPriority(data.get("priority", "medium"))
        except ValueError:
            pass

        status = TaskStatus.PENDING
        try:
            status = TaskStatus(data.get("status", "pending"))
        except ValueError:
            pass

        return cls(
            task_id=data.get("task_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            phase=data.get("phase", ""),
            priority=priority,
            status=status,
            dependencies=data.get("dependencies", []),
            capabilities_required=data.get("capabilities_required", []),
            expected_outputs=data.get("expected_outputs", []),
            acceptance_criteria=data.get("acceptance_criteria", []),
            retry_policy=data.get("retry_policy", {}),
            metadata=data.get("metadata", {}),
        )


@dataclass
class TaskEdge:
    """A dependency edge between two tasks.

    Attributes:
        from_task_id: Source task (must complete first).
        to_task_id: Target task (depends on source).
        type: Edge type (dependency, data_flow, approval).
    """

    from_task_id: str
    to_task_id: str
    type: str = "dependency"


@dataclass
class TaskGraph:
    """Complete directed acyclic graph of project tasks.

    Attributes:
        graph_id: Unique graph identifier.
        project_id: The project this graph belongs to.
        nodes: Map of task_id -> TaskNode.
        edges: List of dependency edges.
        entry_tasks: Task IDs with no dependencies.
        terminal_tasks: Task IDs with no dependents.
        phases: Ordered list of phase names covered by this graph.
    """

    graph_id: str = ""
    project_id: str = ""
    nodes: dict[str, TaskNode] = field(default_factory=dict)
    edges: list[TaskEdge] = field(default_factory=list)
    entry_tasks: list[str] = field(default_factory=list)
    terminal_tasks: list[str] = field(default_factory=list)
    phases: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Resource assignment
# ---------------------------------------------------------------------------


@dataclass
class ResourceAssignment:
    """Assignment of provider, agent, and transport for a task or batch.

    Attributes:
        task_id: The task this assignment is for.
        provider_id: The assigned provider.
        agent_id: The assigned agent.
        transport: The transport type.
        fallback_provider_id: Fallback provider if primary fails.
        fallback_agent_id: Fallback agent if primary fails.
        confidence: Confidence in this assignment.
        reasoning: Why this assignment was made.
    """

    task_id: str = ""
    provider_id: str = ""
    agent_id: str = ""
    transport: str = "rest_api"
    fallback_provider_id: str = ""
    fallback_agent_id: str = ""
    confidence: float = 0.0
    reasoning: str = ""


# ---------------------------------------------------------------------------
# Execution planning
# ---------------------------------------------------------------------------


@dataclass
class ExecutionBatch:
    """A batch of tasks to execute together.

    Attributes:
        batch_id: Unique batch identifier.
        tasks: List of task IDs in this batch.
        mode: Execution mode (parallel, sequential).
        approval_required: Whether human approval is needed before execution.
        verification_points: Verification points after this batch.
        checkpoint_after: Whether to create a checkpoint after this batch.
    """

    batch_id: str = ""
    tasks: list[str] = field(default_factory=list)
    mode: str = "parallel"
    approval_required: bool = False
    verification_points: list[str] = field(default_factory=list)
    checkpoint_after: bool = False


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


@dataclass
class ArtifactCheckResult:
    """Result of checking a single artifact.

    Attributes:
        artifact_name: Name of the artifact checked.
        exists: Whether the artifact exists.
        complete: Whether the artifact is complete.
        integrity_pass: Whether content hash verification passed.
        dependencies_met: Whether all dependencies are satisfied.
        issues: List of issues found.
    """

    artifact_name: str = ""
    exists: bool = False
    complete: bool = False
    integrity_pass: bool = True
    dependencies_met: bool = True
    issues: list[str] = field(default_factory=list)


@dataclass
class VerificationResult:
    """Result of a verification run.

    Attributes:
        scope: Scope of verification.
        target_id: ID of the verified target (task, phase, or project).
        passed: Whether verification passed.
        tests_pass: Whether tests passed.
        lint_pass: Whether linting passed.
        typecheck_pass: Whether typechecking passed.
        contract_valid: Whether contract validation passed.
        artifact_checks: List of artifact check results.
        architecture_valid: Whether architecture validation passed.
        issues: List of issues found.
        warnings: List of warnings.
        retry_suggested: Whether retry is recommended.
    """

    scope: str = ""
    target_id: str = ""
    passed: bool = False
    tests_pass: bool = True
    lint_pass: bool = True
    typecheck_pass: bool = True
    contract_valid: bool = True
    artifact_checks: list[ArtifactCheckResult] = field(default_factory=list)
    architecture_valid: bool = True
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    retry_suggested: bool = False


# ---------------------------------------------------------------------------
# Completion
# ---------------------------------------------------------------------------


@dataclass
class CompletionStatus:
    """Completion status of a task, phase, or project.

    Attributes:
        scope: Scope of completion check.
        target_id: ID of the checked target.
        is_complete: Whether the target is complete.
        completion_percentage: Estimated completion percentage (0-100).
        criteria_met: List of criteria that are met.
        criteria_pending: List of criteria still pending.
        blocked_by: What is blocking completion.
        can_proceed: Whether execution can proceed to next step.
    """

    scope: str = ""
    target_id: str = ""
    is_complete: bool = False
    completion_percentage: float = 0.0
    criteria_met: list[str] = field(default_factory=list)
    criteria_pending: list[str] = field(default_factory=list)
    blocked_by: str = ""
    can_proceed: bool = True


# ---------------------------------------------------------------------------
# Deployment
# ---------------------------------------------------------------------------


@dataclass
class DeploymentPlan:
    """A deployment plan for a project.

    Attributes:
        plan_id: Unique plan identifier.
        project_id: The project this plan is for.
        hosting_platform: Target hosting platform.
        environment_variables: Required environment variables.
        secrets: Required secrets (names only, not values).
        ci_cd_config: CI/CD configuration description.
        monitoring_config: Monitoring configuration.
        rollback_config: Rollback strategy description.
        scaling_config: Scaling configuration.
        additional_steps: Additional deployment steps.
    """

    plan_id: str = ""
    project_id: str = ""
    hosting_platform: str = ""
    environment_variables: list[dict[str, str]] = field(default_factory=list)
    secrets: list[str] = field(default_factory=list)
    ci_cd_config: str = ""
    monitoring_config: str = ""
    rollback_config: str = ""
    scaling_config: str = ""
    additional_steps: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------


@dataclass
class DocumentationSet:
    """Set of generated documentation files.

    Attributes:
        project_id: The project this docs belong to.
        readme: README.md content.
        changelog: CHANGELOG.md content.
        architecture: ARCHITECTURE.md content.
        project_state: PROJECT_STATE.md content.
        tasks: TASKS.md content.
        api: API.md content.
        decisions: DECISIONS.md content.
        additional: Additional documentation files.
    """

    project_id: str = ""
    readme: str = ""
    changelog: str = ""
    architecture: str = ""
    project_state: str = ""
    tasks: str = ""
    api: str = ""
    decisions: str = ""
    additional: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------


@dataclass
class ProgressSnapshot:
    """Snapshot of progress at a point in time.

    Attributes:
        timestamp: ISO-8601 timestamp.
        completed_tasks: Number of completed tasks.
        failed_tasks: Number of failed tasks.
        total_tasks: Total number of tasks.
        retries: Number of retries.
        duration_seconds: Total duration so far.
        provider_usage: Provider usage statistics.
        agent_usage: Agent usage statistics.
        artifacts_produced: Number of artifacts produced.
        milestones_completed: Number of milestones completed.
        contract_completion: Contract completion percentage.
    """

    timestamp: str = ""
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_tasks: int = 0
    retries: int = 0
    duration_seconds: float = 0.0
    provider_usage: dict[str, int] = field(default_factory=dict)
    agent_usage: dict[str, int] = field(default_factory=dict)
    artifacts_produced: int = 0
    milestones_completed: int = 0
    contract_completion: float = 0.0


# ---------------------------------------------------------------------------
# Checkpoints & Rollback
# ---------------------------------------------------------------------------


@dataclass
class CheckpointRecord:
    """A checkpoint recording the state at a point in time.

    Attributes:
        checkpoint_id: Unique checkpoint identifier.
        timestamp: ISO-8601 timestamp.
        checkpoint_type: Type of checkpoint.
        project_state: Serialized project state.
        task_graph: Serialized task graph.
        phase: Current phase when checkpoint was created.
        task_id: Current task ID (if applicable).
        description: Description of this checkpoint.
        artifact_hashes: Content hashes of key artifacts.
    """

    checkpoint_id: str = ""
    timestamp: str = ""
    checkpoint_type: str = "automatic"
    project_state: dict[str, Any] = field(default_factory=dict)
    task_graph: dict[str, Any] = field(default_factory=dict)
    phase: str = ""
    task_id: str = ""
    description: str = ""
    artifact_hashes: dict[str, str] = field(default_factory=dict)


@dataclass
class RollbackResult:
    """Result of a rollback operation.

    Attributes:
        rollback_id: Unique rollback identifier.
        scope: Scope of the rollback.
        target_id: ID of the rolled-back target.
        checkpoint_id: The checkpoint restored to.
        success: Whether the rollback succeeded.
        tasks_rolled_back: Task IDs that were rolled back.
        tasks_preserved: Task IDs that were preserved.
        issues: Issues encountered during rollback.
    """

    rollback_id: str = ""
    scope: str = ""
    target_id: str = ""
    checkpoint_id: str = ""
    success: bool = False
    tasks_rolled_back: list[str] = field(default_factory=list)
    tasks_preserved: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
