"""Execution context for tracking workflow run state.

Tracks workflow ID, execution ID, artifacts, variables, environment,
outputs, and state references throughout a single workflow execution.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class ExecutionContext:
    """Mutable context for a single workflow execution.

    This is the single source of runtime state for a workflow run.
    It is passed through the execution pipeline and updated by
    each component as the workflow progresses.

    Attributes:
        workflow_id: Unique identifier for the workflow definition.
        execution_id: Unique identifier for this execution run.
        run_id: The State Engine run ID (set when execution starts).
        workflow_name: Human-readable workflow name.
        profile: Configuration profile name.
        variables: Mutable key-value store for step inter-communication.
        environment: Environment variables for the execution.
        artifacts: Artifact references produced during execution.
        outputs: Step outputs keyed by step name/index.
        state_refs: State Engine references for persistence.
        metadata: Additional runtime metadata.
        started_at: ISO-8601 start timestamp.
        completed_at: ISO-8601 completion timestamp.
        error: Error message if the execution failed.
    """

    workflow_id: str = ""
    execution_id: str = ""
    run_id: str = ""
    workflow_name: str = ""
    profile: str = "default"
    variables: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, str] = field(default_factory=dict)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    outputs: dict[str, Any] = field(default_factory=dict)
    state_refs: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: str = ""
    completed_at: str = ""
    error: str = ""

    @classmethod
    def create(
        cls,
        workflow_name: str = "",
        workflow_id: str = "",
        execution_id: str | None = None,
        profile: str = "default",
        variables: dict[str, Any] | None = None,
        environment: dict[str, str] | None = None,
    ) -> ExecutionContext:
        """Create a new execution context with auto-generated IDs.

        Args:
            workflow_name: Name of the workflow being executed.
            workflow_id: Unique workflow identifier.
            execution_id: Optional explicit execution ID.
            profile: Configuration profile.
            variables: Initial variables.
            environment: Environment variables.

        Returns:
            A new ExecutionContext.
        """
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            workflow_id=workflow_id or uuid.uuid4().hex[:12],
            execution_id=execution_id or uuid.uuid4().hex[:12],
            workflow_name=workflow_name,
            profile=profile,
            variables=variables or {},
            environment=environment or {},
            started_at=now,
        )

    def set_variable(self, key: str, value: Any) -> None:
        """Set a variable in the execution context.

        Args:
            key: Variable name.
            value: Variable value.
        """
        self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a variable from the execution context.

        Args:
            key: Variable name.
            default: Default value if not found.

        Returns:
            The variable value or default.
        """
        return self.variables.get(key, default)

    def record_output(self, step_name: str, output: dict[str, Any]) -> None:
        """Record a step output.

        Args:
            step_name: Name of the step.
            output: Output data from the step.
        """
        self.outputs[step_name] = output

    def get_output(self, step_name: str, default: Any = None) -> Any:
        """Get a step output.

        Args:
            step_name: Name of the step.
            default: Default value if not found.

        Returns:
            The step output or default.
        """
        return self.outputs.get(step_name, default)

    def add_artifact(self, artifact: dict[str, Any]) -> None:
        """Add an artifact reference.

        Args:
            artifact: Artifact reference data.
        """
        self.artifacts.append(artifact)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary for persistence."""
        return {
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "run_id": self.run_id,
            "workflow_name": self.workflow_name,
            "profile": self.profile,
            "variables": self.variables,
            "environment": self.environment,
            "artifacts": self.artifacts,
            "outputs": self.outputs,
            "state_refs": self.state_refs,
            "metadata": self.metadata,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionContext:
        """Create from a dictionary.

        Args:
            data: Dictionary of context data.

        Returns:
            A new ExecutionContext.
        """
        return cls(
            workflow_id=data.get("workflow_id", ""),
            execution_id=data.get("execution_id", ""),
            run_id=data.get("run_id", ""),
            workflow_name=data.get("workflow_name", ""),
            profile=data.get("profile", "default"),
            variables=data.get("variables", {}),
            environment=data.get("environment", {}),
            artifacts=data.get("artifacts", []),
            outputs=data.get("outputs", {}),
            state_refs=data.get("state_refs", {}),
            metadata=data.get("metadata", {}),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at", ""),
            error=data.get("error", ""),
        )
