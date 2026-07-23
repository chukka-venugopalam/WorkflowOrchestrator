"""Execution engine — runs executable steps, dispatches, tracks, and collects outputs.

The Execution Engine is the core runtime that:
- Runs executable steps (via StepExecutor)
- Dispatches to plugins
- Tracks execution progress
- Collects and records outputs
- Publishes events to the Event Bus
- Updates the State Engine
- Handles retries via the Retry Engine
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from workflow_orchestrator.execution.execution_context import ExecutionContext
from workflow_orchestrator.execution.execution_queue import ExecutionQueue
from workflow_orchestrator.execution.retry_engine import (
    RetryEngine,
    RetryPolicy,
    RetryState,
    RetryDecision,
)
from workflow_orchestrator.execution.step_executor import StepExecutor
from workflow_orchestrator.execution.workflow_compiler import ExecutionGraph, ExecutionNode
from workflow_orchestrator.models import StepResult, StepStatus

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """Executes workflow steps with dispatch, tracking, events, and state updates.

    The Execution Engine orchestrates the actual running of steps. It works
    with the StepExecutor (one step at a time), the ExecutionQueue (scheduling),
    the RetryEngine (failure recovery), and integrates with the EventBus and
    StateEngine for observability and persistence.

    This engine knows NOTHING about:
    - Workflow loading/validation/compilation
    - AI providers or agents
    - Capability matching or routing
    - What to execute — only HOW to execute.

    Usage:
        >>> engine = ExecutionEngine(executor=step_executor)
        >>> result = engine.execute_node(node, context)
    """

    def __init__(
        self,
        executor: StepExecutor | None = None,
        retry_engine: RetryEngine | None = None,
        event_bus: Any = None,
        state_engine: Any = None,
    ) -> None:
        """Initialize the execution engine.

        Args:
            executor: Step executor for running individual steps.
            retry_engine: Engine for retry logic.
            event_bus: Optional EventBus for publishing execution events.
            state_engine: Optional StateEngine for persisting run state.
        """
        self._executor = executor or StepExecutor()
        self._retry_engine = retry_engine or RetryEngine()
        self._event_bus = event_bus
        self._state_engine = state_engine

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def executor(self) -> StepExecutor:
        """The underlying step executor."""
        return self._executor

    @property
    def retry_engine(self) -> RetryEngine:
        """The underlying retry engine."""
        return self._retry_engine

    @property
    def event_bus(self) -> Any:
        """The event bus, if set."""
        return self._event_bus

    @property
    def state_engine(self) -> Any:
        """The state engine, if set."""
        return self._state_engine

    # ------------------------------------------------------------------
    # Node execution
    # ------------------------------------------------------------------

    def execute_node(
        self,
        node: ExecutionNode,
        context: ExecutionContext,
        retry_policy: RetryPolicy | None = None,
    ) -> StepResult:
        """Execute a single node, with optional retry logic.

        Args:
            node: The execution node to execute.
            context: The current execution context.
            retry_policy: Retry policy. Uses default if None.

        Returns:
            The final StepResult after all retry attempts.
        """
        policy = retry_policy or RetryPolicy(
            max_retries=node.retry_config.get("max_retries", 0),
            delay=node.retry_config.get("delay", 1.0),
            backoff=node.retry_config.get("backoff", 2.0),
        )

        self._publish_event("step.started", {
            "node_id": node.node_id,
            "step_name": node.name,
            "plugin": node.plugin,
            "execution_id": context.execution_id,
        })

        # Set up retry state
        retry_state = RetryState(
            step_name=node.name or node.node_id,
            max_retries=policy.max_retries + 1,  # +1 for initial attempt
            started_at=time.time(),
        )

        attempt = 1
        while True:
            logger.debug(
                "Executing node '%s' (attempt %d/%d)",
                node.node_id,
                attempt,
                retry_state.max_retries,
            )

            result = self._executor.execute(node, context)

            # Record step execution in context
            self._update_context(context, node, result)

            # If successful, we're done
            if result.status == StepStatus.SUCCESS:
                self._publish_event("step.completed", {
                    "node_id": node.node_id,
                    "step_name": node.name,
                    "duration": result.duration,
                    "execution_id": context.execution_id,
                })
                return result

            # Check if we should retry
            if attempt >= retry_state.max_retries:
                # No more retries available — return the failure
                self._publish_event("step.failed", {
                    "node_id": node.node_id,
                    "step_name": node.name,
                    "error": result.error,
                    "duration": result.duration,
                    "execution_id": context.execution_id,
                })
                return result

            # If on_failure is "continue", skip retry and move on
            on_failure = node.on_failure or "stop"
            if on_failure == "continue":
                self._publish_event("step.failed", {
                    "node_id": node.node_id,
                    "step_name": node.name,
                    "action": "continue",
                    "execution_id": context.execution_id,
                })
                return result

            # Evaluate retry
            decision, updated_state = self._retry_engine.evaluate(
                retry_state, result, policy
            )
            retry_state = updated_state

            if decision == RetryDecision.RETRY:
                # Wait with backoff before retrying
                self._retry_engine.wait_and_retry(retry_state, policy)
                attempt += 1
                self._publish_event("step.retrying", {
                    "node_id": node.node_id,
                    "step_name": node.name,
                    "attempt": attempt,
                    "delay": retry_state.delay,
                    "execution_id": context.execution_id,
                })
                continue

            # Not retrying — abort or escalate
            self._publish_event("step.failed", {
                "node_id": node.node_id,
                "step_name": node.name,
                "decision": decision.value,
                "error": result.error,
                "execution_id": context.execution_id,
            })
            return result

    # ------------------------------------------------------------------
    # Context management
    # ------------------------------------------------------------------

    def _update_context(
        self,
        context: ExecutionContext,
        node: ExecutionNode,
        result: StepResult,
    ) -> None:
        """Update the execution context with step results.

        Args:
            context: The execution context to update.
            node: The node that was executed.
            result: The step result.
        """
        context.record_output(node.node_id, result.output)

        if result.status == StepStatus.SUCCESS:
            context.set_variable(f"{node.node_id}.status", "success")
        else:
            context.set_variable(f"{node.node_id}.status", "failed")
            context.set_variable(f"{node.node_id}.error", result.error)

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an execution event if an event bus is available.

        Args:
            event_type: The event type string (e.g., ``step.started``).
            data: The event payload.
        """
        if self._event_bus is None:
            return

        try:
            from workflow_orchestrator.core.event_bus import Event
            self._event_bus.publish(Event(
                type=event_type,
                data=data,
                source="execution_engine",
            ))
        except Exception:
            logger.warning("Failed to publish event '%s'", event_type, exc_info=True)

    # ------------------------------------------------------------------
    # State engine integration
    # ------------------------------------------------------------------

    def update_run_state(
        self,
        run_id: str,
        status: str,
        step_index: int = 0,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Update run state if a state engine is available.

        Args:
            run_id: The run identifier.
            status: The new status.
            step_index: Current step index.
            data: Optional transition data.
        """
        if self._state_engine is None:
            return

        try:
            self._state_engine.transition(
                run_id=run_id,
                to_status=status,
                actor="execution_engine",
                data=data,
            )
            self._state_engine.record_heartbeat(
                run_id=run_id,
                step_index=step_index,
            )
        except Exception:
            logger.warning("Failed to update run state for '%s'", run_id, exc_info=True)

    def start_run(self, context: ExecutionContext) -> str:
        """Start tracking a new run in the state engine.

        Args:
            context: The execution context.

        Returns:
            The run ID.
        """
        run_id = context.run_id or context.execution_id
        context.run_id = run_id

        if self._state_engine:
            try:
                snapshot = self._state_engine.create_run(
                    workflow_name=context.workflow_name,
                    run_id=run_id,
                    data={"execution_id": context.execution_id},
                )
                self._state_engine.transition(
                    run_id=run_id,
                    to_status="running",
                    actor="execution_engine",
                    data={
                        "workflow_id": context.workflow_id,
                        "profile": context.profile,
                    },
                )
            except Exception:
                logger.warning("Failed to start run '%s' in state engine", run_id, exc_info=True)

        return run_id

    def complete_run(self, context: ExecutionContext, success: bool = True) -> None:
        """Mark a run as completed or failed in the state engine.

        Args:
            context: The execution context.
            success: True for completed, False for failed.
        """
        status = "completed" if success else "failed"

        if self._state_engine:
            try:
                self._state_engine.transition(
                    run_id=context.run_id,
                    to_status=status,
                    actor="execution_engine",
                    data={"execution_id": context.execution_id},
                )
                self._state_engine.record_heartbeat(
                    run_id=context.run_id,
                    step_index=len(context.outputs),
                )
            except Exception:
                logger.warning("Failed to complete run '%s'", context.run_id, exc_info=True)
