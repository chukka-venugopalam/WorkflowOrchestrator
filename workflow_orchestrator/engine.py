"""Workflow engine for executing automation workflows.

The engine loads workflow definitions (from YAML files or
programmatically), resolves plugins for each step, executes
steps sequentially with error recovery (retry / continue / stop),
and produces execution reports.
"""

from __future__ import annotations

import copy
import logging
import time
import traceback
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.models import (
    ExecutionReport,
    OnFailure,
    RetryConfig,
    StepResult,
    StepStatus,
    WorkflowDefinition,
    WorkflowStep,
)
from workflow_orchestrator.plugins.registry import PluginRegistry, default_registry

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Executes workflow definitions step by step.

    The engine is reusable: call ``execute()`` with different
    workflows to run them.  Each call produces a new
    ``ExecutionReport``.

    Usage:
        >>> engine = WorkflowEngine()
        >>> report = engine.execute(workflow_definition)
        >>> print(report.success)
    """

    def __init__(
        self,
        plugin_registry: PluginRegistry | None = None,
    ) -> None:
        """Initialize the engine.

        Args:
            plugin_registry: Registry to resolve plugin names.
                Defaults to the application-wide ``default_registry``.
        """
        self._registry = plugin_registry or default_registry
        self._abort_requested = False

    def abort(self) -> None:
        """Request graceful abort of the currently running workflow."""
        self._abort_requested = True
        logger.info("Abort requested for running workflow.")

    @property
    def registry(self) -> PluginRegistry:
        """The plugin registry used by this engine."""
        return self._registry

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(
        self,
        workflow: WorkflowDefinition,
        context: dict[str, Any] | None = None,
        profile: str = "default",
    ) -> ExecutionReport:
        """Execute a workflow definition.

        Args:
            workflow: The workflow to execute.
            context: Optional shared context dictionary passed to
                every step.  Can be used to pass values between steps.
            profile: The configuration profile name used for this run.

        Returns:
            ExecutionReport: Full report of the execution.
        """
        self._abort_requested = False
        start_time = time.time()
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

        report = ExecutionReport(
            workflow_name=workflow.name,
            workflow_source=workflow.source,
            timestamp=timestamp,
            profile=profile,
            total_steps=len(workflow.steps),
        )

        ctx: dict[str, Any] = copy.deepcopy(context) or {}

        logger.info(
            "Starting workflow '%s' (%d steps) with profile '%s'",
            workflow.name,
            len(workflow.steps),
            profile,
        )
        report.logs.append(f"[{timestamp}] Workflow '{workflow.name}' started.")

        for step_index, step in enumerate(workflow.steps, start=1):
            if self._abort_requested:
                logger.warning("Workflow aborted at step %d.", step_index)
                report.logs.append(f"Workflow aborted at step {step_index}.")
                report.success = False
                report.error = "Aborted by user"
                break

            step_result = self._execute_step(step, step_index, ctx)
            report.steps.append(step_result)

            if step_result.status == StepStatus.SUCCESS:
                report.successful_steps += 1
            elif step_result.status == StepStatus.FAILURE:
                report.failed_steps += 1
                report.success = False

            # Handle error recovery
            if step_result.status == StepStatus.FAILURE:
                if step.on_failure == OnFailure.STOP:
                    report.error = f"Step '{step.name or step.plugin}' failed: {step_result.error}"
                    logger.error("Workflow stopped at step %d: %s", step_index, report.error)
                    report.logs.append(f"Workflow stopped: {report.error}")
                    break
                elif step.on_failure == OnFailure.CONTINUE:
                    logger.warning(
                        "Step %d failed but continuing: %s",
                        step_index,
                        step_result.error,
                    )
                    report.logs.append(f"Step {step_index} failed, continuing: {step_result.error}")
                    continue
                # OnFailure.RETRY is handled inside _execute_step

        end_time = time.time()
        report.duration = end_time - start_time

        logger.info(
            "Workflow '%s' completed: %d/%d steps successful (%.2f s)",
            workflow.name,
            report.successful_steps,
            report.total_steps,
            report.duration,
        )
        report.logs.append(
            f"Workflow completed: {report.successful_steps}/{report.total_steps} steps "
            f"successful in {report.duration:.2f}s."
        )

        return report

    def execute_yaml(
        self,
        yaml_path: Path | str,
        context: dict[str, Any] | None = None,
        profile: str = "default",
    ) -> ExecutionReport:
        """Load a YAML workflow and execute it.

        Args:
            yaml_path: Path to the YAML workflow file.
            context: Optional shared context dictionary.
            profile: Configuration profile name.

        Returns:
            ExecutionReport: Full execution report.
        """
        path = Path(yaml_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Workflow file not found: {path}")

        workflow = WorkflowDefinition.from_yaml(path)
        return self.execute(workflow, context=context, profile=profile)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute_step(
        self,
        step: WorkflowStep,
        step_index: int,
        context: dict[str, Any],
    ) -> StepResult:
        """Execute a single workflow step, with retry logic.

        Args:
            step: The step definition.
            step_index: 1-based step index for logging.
            context: Shared execution context (mutated in place).

        Returns:
            StepResult: The final result after any retries.
        """
        plugin = self._registry.get(step.plugin)
        if plugin is None:
            return StepResult(
                step_name=step.name or f"Step {step_index}",
                plugin=step.plugin,
                status=StepStatus.FAILURE,
                message=f"Plugin '{step.plugin}' not found.",
                error=f"No plugin registered with name '{step.plugin}'. "
                       f"Available: {self._registry.names}",
            )

        # Inject step name into config for plugin use
        step_config = copy.deepcopy(step.config)
        step_name = step.name or f"{step.plugin}:{step_index}"
        step_config["_step_name"] = step_name

        max_retries = step.retry.max_retries
        delay = step.retry.delay
        backoff = step.retry.backoff

        last_result: StepResult | None = None

        for attempt in range(1, max_retries + 2):  # +1 for the initial attempt
            if self._abort_requested:
                return StepResult(
                    step_name=step_name,
                    plugin=step.plugin,
                    status=StepStatus.SKIPPED,
                    message="Workflow aborted.",
                )

            attempt_start = time.time()

            try:
                result = plugin.execute(step_config, context)
            except Exception as exc:
                result = StepResult(
                    step_name=step_name,
                    plugin=step.plugin,
                    status=StepStatus.FAILURE,
                    message=f"Plugin raised an exception: {exc}",
                    error=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
                )

            result.attempts = attempt
            result.duration = time.time() - attempt_start

            if result.status == StepStatus.SUCCESS:
                # Store output in context for subsequent steps
                if result.output:
                    context[f"step_{step_index}_output"] = result.output
                    context[f"{step.plugin}_last_output"] = result.output
                return result

            # Failure — check if we should retry
            last_result = result

            if attempt <= max_retries:
                retry_delay = delay * (backoff ** (attempt - 1))
                logger.info(
                    "Retrying step '%s' (attempt %d/%d) in %.1fs...",
                    step_name,
                    attempt,
                    max_retries + 1,
                    retry_delay,
                )
                time.sleep(retry_delay)
            else:
                break

        # All retries exhausted
        if last_result is None:
            last_result = StepResult(
                step_name=step_name,
                plugin=step.plugin,
                status=StepStatus.FAILURE,
                message="Step failed with no result.",
                error="Unknown error",
            )

        return last_result
