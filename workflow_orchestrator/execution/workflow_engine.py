"""Workflow engine — orchestrates the full lifecycle of workflow execution.

The Workflow Engine is the top-level coordinator that:
- Loads workflow definitions (YAML/JSON)
- Validates workflow structure and dependencies
- Compiles workflows into execution graphs
- Schedules and dispatches steps for execution
- Monitors execution progress
- Handles cancellation, pause, and resume
- Manages the ExecutionContext through the full lifecycle
- Integrates with State Engine, Event Bus, Artifact Manager

This engine knows NOTHING about AI providers or agents.
"""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Any

from workflow_orchestrator.execution.execution_context import ExecutionContext
from workflow_orchestrator.execution.execution_engine import ExecutionEngine
from workflow_orchestrator.execution.execution_queue import ExecutionQueue
from workflow_orchestrator.execution.step_executor import StepExecutor
from workflow_orchestrator.execution.workflow_compiler import (
    ExecutionGraph,
    ExecutionNode,
    WorkflowCompiler,
)
from workflow_orchestrator.execution.workflow_loader import WorkflowLoader
from workflow_orchestrator.execution.workflow_validator import (
    ValidationResult,
    WorkflowValidator,
)
from workflow_orchestrator.execution.dependency_resolver import DependencyResolver
from workflow_orchestrator.models import StepResult, StepStatus, WorkflowDefinition

logger = logging.getLogger(__name__)

# Workflow run statuses
WORKFLOW_STATUS_PENDING = "pending"
WORKFLOW_STATUS_RUNNING = "running"
WORKFLOW_STATUS_PAUSED = "paused"
WORKFLOW_STATUS_COMPLETED = "completed"
WORKFLOW_STATUS_FAILED = "failed"
WORKFLOW_STATUS_CANCELLED = "cancelled"


class WorkflowRun:
    """Represents a single workflow run with its live state.

    Attributes:
        run_id: Unique identifier for this run.
        workflow_name: Name of the workflow being executed.
        graph: The compiled execution graph.
        context: The execution context.
        status: Current run status.
        completed_nodes: Set of completed step node IDs.
        failed_nodes: Set of failed step node IDs.
        step_results: Results keyed by node ID.
        started_at: Timestamp when execution started.
    """

    def __init__(
        self,
        run_id: str,
        workflow_name: str,
        graph: ExecutionGraph,
        context: ExecutionContext,
    ) -> None:
        self.run_id: str = run_id
        self.workflow_name: str = workflow_name
        self.graph: ExecutionGraph = graph
        self.context: ExecutionContext = context
        self.status: str = WORKFLOW_STATUS_PENDING
        self.completed_nodes: set[str] = set()
        self.failed_nodes: set[str] = set()
        self.step_results: dict[str, StepResult] = {}
        self.started_at: float = 0.0
        self.completed_at: float = 0.0


class WorkflowEngine:
    """Top-level orchestrator for the full workflow lifecycle.

    Coordinates loading, validation, compilation, scheduling, monitoring,
    cancellation, pause, and resume of workflows.

    Usage:
        >>> engine = WorkflowEngine()
        >>> run = engine.run("workflows/example.yaml")
        >>> print(run.status)
        'completed'
    """

    def __init__(
        self,
        loader: WorkflowLoader | None = None,
        validator: WorkflowValidator | None = None,
        compiler: WorkflowCompiler | None = None,
        resolver: DependencyResolver | None = None,
        execution_engine: ExecutionEngine | None = None,
        queue: ExecutionQueue | None = None,
        event_bus: Any = None,
        state_engine: Any = None,
        artifact_manager: Any = None,
    ) -> None:
        """Initialize the workflow engine.

        Args:
            loader: Workflow loader for loading definitions.
            validator: Workflow validator.
            compiler: Workflow compiler.
            resolver: Dependency resolver.
            execution_engine: Engine for running steps.
            queue: Execution queue for scheduling.
            event_bus: Optional EventBus for publishing events.
            state_engine: Optional StateEngine for persistence.
            artifact_manager: Optional ArtifactManager for storing artifacts.
        """
        self._loader = loader or WorkflowLoader()
        self._validator = validator or WorkflowValidator()
        self._compiler = compiler or WorkflowCompiler()
        self._resolver = resolver or DependencyResolver()
        self._execution_engine = execution_engine or ExecutionEngine()
        self._queue = queue or ExecutionQueue()
        self._event_bus = event_bus
        self._state_engine = state_engine
        self._artifact_manager = artifact_manager

        # Active runs
        self._runs: dict[str, WorkflowRun] = {}

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def runs(self) -> dict[str, WorkflowRun]:
        """All active/finished runs keyed by run ID."""
        return dict(self._runs)

    @property
    def active_runs(self) -> list[WorkflowRun]:
        """List of currently running workflow runs."""
        return [r for r in self._runs.values() if r.status == WORKFLOW_STATUS_RUNNING]

    @property
    def loader(self) -> WorkflowLoader:
        """The workflow loader."""
        return self._loader

    @property
    def execution_engine(self) -> ExecutionEngine:
        """The execution engine."""
        return self._execution_engine

    # ------------------------------------------------------------------
    # Main execution flow
    # ------------------------------------------------------------------

    def run(
        self,
        workflow_source: Path | str | WorkflowDefinition,
        execution_id: str | None = None,
        run_id: str | None = None,
        profile: str = "default",
        variables: dict[str, Any] | None = None,
        environment: dict[str, str] | None = None,
    ) -> WorkflowRun:
        """Run a workflow from source, definition, or file path.

        This is the primary entry point for executing workflows. It
        performs the full lifecycle: load → validate → compile → execute.

        Args:
            workflow_source: Path to a workflow file, or a WorkflowDefinition.
            execution_id: Optional explicit execution ID.
            run_id: Optional explicit run ID (for State Engine).
            profile: Configuration profile name.
            variables: Initial variables for the execution context.
            environment: Environment variables for the execution context.

        Returns:
            A WorkflowRun with execution results.

        Raises:
            FileNotFoundError: If the workflow source file does not exist.
            ValueError: If the workflow is invalid.
        """
        # Phase 1: Load
        workflow = self._resolve_workflow(workflow_source)
        logger.info("Running workflow '%s' (%d steps)", workflow.name, len(workflow.steps))

        # Phase 2: Validate
        validation = self._validator.validate(workflow)
        if not validation.valid:
            error_msg = "; ".join(validation.errors)
            logger.error("Workflow validation failed: %s", error_msg)
            raise ValueError(f"Workflow validation failed: {error_msg}")

        # Phase 3: Compile
        graph = validation.graph or self._compiler.compile(workflow)
        logger.debug(
            "Compiled workflow: %d nodes, %d edges",
            len(graph.nodes),
            len(graph.edges),
        )

        # Phase 4: Create execution context and run tracking
        context = ExecutionContext.create(
            workflow_name=workflow.name,
            workflow_id=graph.workflow_id,
            execution_id=execution_id,
            profile=profile,
            variables=variables,
            environment=environment,
        )

        run = WorkflowRun(
            run_id=run_id or context.execution_id,
            workflow_name=workflow.name,
            graph=graph,
            context=context,
        )
        self._runs[run.run_id] = run

        # Phase 5: Execute
        self._execute_run(run)

        return run

    def _resolve_workflow(
        self,
        source: Path | str | WorkflowDefinition,
    ) -> WorkflowDefinition:
        """Resolve a workflow from different input types.

        Args:
            source: Path, string, or WorkflowDefinition.

        Returns:
            A WorkflowDefinition.
        """
        if isinstance(source, WorkflowDefinition):
            return source
        return self._loader.load(Path(str(source)))

    # ------------------------------------------------------------------
    # Internal execution
    # ------------------------------------------------------------------

    def _execute_run(self, run: WorkflowRun) -> None:
        """Execute a prepared workflow run.

        Args:
            run: The WorkflowRun to execute.
        """
        run.status = WORKFLOW_STATUS_RUNNING
        run.started_at = time.time()

        self._publish_event("workflow.started", {
            "run_id": run.run_id,
            "workflow_name": run.workflow_name,
            "node_count": len(run.graph.nodes),
        })

        # Start state engine tracking
        self._execution_engine.start_run(run.context)

        # Resolve execution order
        order = self._resolver.resolve(run.graph)
        if order.has_cycles:
            error_msg = f"Circular dependency detected: {order.cycle_paths}"
            logger.error(error_msg)
            run.status = WORKFLOW_STATUS_FAILED
            run.context.error = error_msg
            self._execution_engine.complete_run(run.context, success=False)
            return

        # Execute steps in order
        for node_id in order.node_ids:
            node = run.graph.nodes.get(node_id)
            if node is None:
                logger.warning("Node '%s' not found in graph, skipping", node_id)
                continue

            # Check if run was cancelled or paused
            if run.status == WORKFLOW_STATUS_CANCELLED:
                logger.info("Run '%s' was cancelled, stopping execution", run.run_id)
                break
            if run.status == WORKFLOW_STATUS_PAUSED:
                logger.info("Run '%s' was paused, stopping execution", run.run_id)
                break

            # Execute the node
            result = self._execution_engine.execute_node(node, run.context)

            # Record the result
            run.step_results[node_id] = result

            if result.status == StepStatus.SUCCESS:
                run.completed_nodes.add(node_id)
            else:
                run.failed_nodes.add(node_id)
                # Check on_failure action
                if node.on_failure == "stop":
                    logger.error(
                        "Step '%s' failed with on_failure=stop, aborting workflow",
                        node.name or node_id,
                    )
                    run.status = WORKFLOW_STATUS_FAILED
                    run.context.error = result.error
                    break
                elif node.on_failure == "continue":
                    logger.warning(
                        "Step '%s' failed but on_failure=continue, moving on",
                        node.name or node_id,
                    )
                    continue
                # on_failure="retry" is handled inside execute_node

        # Complete the run
        run.completed_at = time.time()
        duration = run.completed_at - run.started_at

        if run.status == WORKFLOW_STATUS_CANCELLED:
            pass  # Status already set
        elif run.status == WORKFLOW_STATUS_PAUSED:
            pass  # Status already set
        elif run.status == WORKFLOW_STATUS_FAILED:
            pass  # Already set during step failure
        else:
            run.status = WORKFLOW_STATUS_COMPLETED if len(run.failed_nodes) == 0 else WORKFLOW_STATUS_FAILED

        self._execution_engine.complete_run(run.context, success=(run.status == WORKFLOW_STATUS_COMPLETED))

        self._publish_event("workflow.completed", {
            "run_id": run.run_id,
            "workflow_name": run.workflow_name,
            "status": run.status,
            "duration": round(duration, 3),
            "completed_nodes": len(run.completed_nodes),
            "failed_nodes": len(run.failed_nodes),
        })

        logger.info(
            "Workflow '%s' completed: %s (%.2fs, %d/%d steps succeeded)",
            run.workflow_name,
            run.status,
            duration,
            len(run.completed_nodes),
            len(run.graph.nodes),
        )

    # ------------------------------------------------------------------
    # Run management
    # ------------------------------------------------------------------

    def get_run(self, run_id: str) -> WorkflowRun | None:
        """Get a workflow run by ID.

        Args:
            run_id: The run identifier.

        Returns:
            The WorkflowRun, or None if not found.
        """
        return self._runs.get(run_id)

    def cancel_run(self, run_id: str) -> bool:
        """Cancel a running workflow.

        Args:
            run_id: The run identifier.

        Returns:
            True if cancelled, False if run not found.
        """
        run = self._runs.get(run_id)
        if run is None:
            return False

        if run.status in (WORKFLOW_STATUS_COMPLETED, WORKFLOW_STATUS_FAILED, WORKFLOW_STATUS_CANCELLED):
            logger.warning("Run '%s' is already in terminal state '%s'", run_id, run.status)
            return False

        run.status = WORKFLOW_STATUS_CANCELLED
        logger.info("Cancelled run '%s'", run_id)

        self._publish_event("workflow.cancelled", {
            "run_id": run_id,
            "workflow_name": run.workflow_name,
        })
        return True

    def pause_run(self, run_id: str) -> bool:
        """Pause a running workflow.

        Args:
            run_id: The run identifier.

        Returns:
            True if paused, False if run not found or not running.
        """
        run = self._runs.get(run_id)
        if run is None:
            return False
        if run.status != WORKFLOW_STATUS_RUNNING:
            return False

        run.status = WORKFLOW_STATUS_PAUSED
        logger.info("Paused run '%s'", run_id)

        self._publish_event("workflow.paused", {
            "run_id": run_id,
            "workflow_name": run.workflow_name,
        })
        return True

    def resume_run(self, run_id: str) -> bool:
        """Resume a paused workflow.

        Args:
            run_id: The run identifier.

        Returns:
            True if resumed, False if run not found or not paused.
        """
        run = self._runs.get(run_id)
        if run is None:
            return False
        if run.status != WORKFLOW_STATUS_PAUSED:
            return False

        run.status = WORKFLOW_STATUS_RUNNING
        logger.info("Resumed run '%s'", run_id)

        self._publish_event("workflow.resumed", {
            "run_id": run_id,
            "workflow_name": run.workflow_name,
        })
        return True

    def list_runs(self, status: str | None = None) -> list[WorkflowRun]:
        """List workflow runs, optionally filtered by status.

        Args:
            status: Optional status filter.

        Returns:
            List of WorkflowRun objects.
        """
        if status:
            return [r for r in self._runs.values() if r.status == status]
        return list(self._runs.values())

    def run_summary(self, run_id: str) -> dict[str, Any]:
        """Get a summary of a workflow run.

        Args:
            run_id: The run identifier.

        Returns:
            Dict with run summary information.
        """
        run = self._runs.get(run_id)
        if run is None:
            return {"error": f"Run '{run_id}' not found"}

        return {
            "run_id": run.run_id,
            "workflow_name": run.workflow_name,
            "status": run.status,
            "total_nodes": len(run.graph.nodes),
            "completed_nodes": len(run.completed_nodes),
            "failed_nodes": len(run.failed_nodes),
            "step_results": {
                nid: {
                    "status": r.status.value,
                    "duration": r.duration,
                    "message": r.message,
                }
                for nid, r in run.step_results.items()
            },
            "variables": dict(run.context.variables),
            "started_at": run.started_at,
            "completed_at": run.completed_at,
        }

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish a workflow event if an event bus is available.

        Args:
            event_type: The event type string.
            data: The event payload.
        """
        if self._event_bus is None:
            return

        try:
            from workflow_orchestrator.core.event_bus import Event
            self._event_bus.publish(Event(
                type=event_type,
                data=data,
                source="workflow_engine",
            ))
        except Exception:
            logger.debug("Failed to publish event '%s'", event_type, exc_info=True)
