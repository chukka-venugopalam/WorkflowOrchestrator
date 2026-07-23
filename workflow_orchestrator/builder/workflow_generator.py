"""Workflow Generator — automatically converts task graph into executable workflow YAML files.

Generates complete WorkflowDefinition YAML files that the WorkflowEngine
can load and execute. No manual workflow writing required.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import yaml

from workflow_orchestrator.builder.data_models import TaskGraph, TaskNode
from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class WorkflowGenerator:
    """Converts a TaskGraph into executable workflow YAML files.

    Each phase in the task graph becomes a separate workflow file.
    Workflows include proper step configuration, retry policies,
    and failure handling.

    Usage:
        >>> generator = WorkflowGenerator()
        >>> paths = generator.generate(graph, "/path/to/workflows")
        >>> print(paths)
        ['/path/to/workflows/phase_1_foundation.yaml', ...]
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Workflow Generator.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(
        self,
        task_graph: TaskGraph,
        output_dir: str | Path,
    ) -> list[str]:
        """Generate workflow YAML files from a task graph.

        Args:
            task_graph: The task graph to convert.
            output_dir: Directory to write workflow files to.

        Returns:
            List of paths to generated workflow files.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        generated_paths: list[str] = []

        # Group tasks by phase
        phases: dict[str, list[TaskNode]] = {}
        for node in task_graph.nodes.values():
            if node.phase not in phases:
                phases[node.phase] = []
            phases[node.phase].append(node)

        # Generate a workflow for each phase
        for phase_name, tasks in phases.items():
            workflow_path = self._generate_phase_workflow(
                phase_name, tasks, task_graph, output_path,
            )
            generated_paths.append(str(workflow_path))

        # Generate a master workflow that orchestrates all phases
        master_path = self._generate_master_workflow(
            list(phases.keys()), output_path,
        )
        generated_paths.append(str(master_path))

        self._publish_event("builder.workflow_generated", {
            "workflow_count": len(generated_paths),
            "output_dir": str(output_path),
        })

        logger.info("Generated %d workflow files in %s", len(generated_paths), output_path)
        return generated_paths

    def _generate_phase_workflow(
        self,
        phase_name: str,
        tasks: list[TaskNode],
        task_graph: TaskGraph,
        output_path: Path,
    ) -> Path:
        """Generate a workflow YAML file for a single phase.

        Args:
            phase_name: The phase name.
            tasks: The tasks in this phase.
            task_graph: The full task graph.
            output_path: Output directory.

        Returns:
            Path to the generated YAML file.
        """
        readable_name = phase_name.replace("_", " ").title()
        filename = f"phase_{phase_name}.yaml"

        steps: list[dict[str, Any]] = []
        for task in tasks:
            step_config: dict[str, Any] = {
                "name": task.name,
                "plugin": "agent",
                "config": {
                    "task_id": task.task_id,
                    "goal": task.description,
                    "capabilities": task.capabilities_required,
                    "expected_outputs": task.expected_outputs,
                },
                "on_failure": "retry",
                "retry": task.retry_policy,
            }

            if task.dependencies:
                step_config["config"]["depends_on"] = task.dependencies

            steps.append(step_config)

        workflow = {
            "name": f"{readable_name} - Phase",
            "description": f"Implementation phase: {readable_name}",
            "tags": [phase_name, "builder"],
            "steps": steps,
        }

        filepath = output_path / filename
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(workflow, f, default_flow_style=False, sort_keys=False, indent=2)

        logger.debug("Generated workflow '%s' with %d steps", filename, len(steps))
        return filepath

    def _generate_master_workflow(
        self,
        phase_names: list[str],
        output_path: Path,
    ) -> Path:
        """Generate a master orchestrator workflow.

        Args:
            phase_names: Ordered list of phase names.
            output_path: Output directory.

        Returns:
            Path to the generated YAML file.
        """
        steps: list[dict[str, Any]] = []
        previous_phase = ""

        for phase_name in phase_names:
            readable_name = phase_name.replace("_", " ").title()
            filename = f"phase_{phase_name}.yaml"

            step_config: dict[str, Any] = {
                "name": f"Phase: {readable_name}",
                "plugin": "workflow",
                "config": {
                    "workflow_file": filename,
                    "phase": phase_name,
                },
                "on_failure": "stop",
                "retry": {"max_retries": 1},
            }

            if previous_phase:
                step_config["config"]["depends_on"] = [f"step_{phase_names.index(previous_phase) + 1}"]

            steps.append(step_config)
            previous_phase = phase_name

        master = {
            "name": "Master Orchestrator",
            "description": "Master workflow orchestrating all project phases",
            "tags": ["master", "builder", "orchestrator"],
            "steps": steps,
        }

        filepath = output_path / "master_workflow.yaml"
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(master, f, default_flow_style=False, sort_keys=False, indent=2)

        return filepath

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(
                type=event_type, data=data, source="workflow_generator",
            ))
        except Exception:
            pass
