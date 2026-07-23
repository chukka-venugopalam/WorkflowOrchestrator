"""Completion Checker — determines whether tasks, phases, and projects are complete.

Checks:
- Task complete: All acceptance criteria met
- Phase complete: All tasks in phase complete and verified
- Project complete: All phases complete and contract satisfied
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.builder.data_models import (
    CompletionStatus,
    TaskGraph,
    TaskStatus,
)
from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class CompletionChecker:
    """Determines completion status at the task, phase, and project levels.

    Usage:
        >>> checker = CompletionChecker()
        >>> status = checker.check_task("task_001", task_graph, verification_result)
        >>> print(status.is_complete)
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Completion Checker.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # Task completion
    # ------------------------------------------------------------------

    def check_task(
        self,
        task_id: str,
        task_graph: TaskGraph,
        verification_result: Any = None,
        task_outputs: dict[str, Any] | None = None,
    ) -> CompletionStatus:
        """Check if a task is complete.

        Args:
            task_id: The task identifier.
            task_graph: The task graph containing the task.
            verification_result: Optional verification result.
            task_outputs: Optional task outputs.

        Returns:
            CompletionStatus for the task.
        """
        node = task_graph.nodes.get(task_id)
        if node is None:
            return CompletionStatus(
                scope="task",
                target_id=task_id,
                is_complete=False,
                completion_percentage=0.0,
                criteria_pending=["Task not found"],
                blocked_by="Task not found in graph",
                can_proceed=False,
            )

        criteria_met: list[str] = []
        criteria_pending: list[str] = []

        # Check execution status
        if node.status == TaskStatus.COMPLETED:
            criteria_met.append("Task executed successfully")
        elif node.status == TaskStatus.SKIPPED:
            criteria_met.append("Task was skipped")
        elif node.status == TaskStatus.FAILED:
            criteria_pending.append("Task execution failed")
        else:
            criteria_pending.append(f"Task status: {node.status.value}")

        # Check acceptance criteria
        for criterion in node.acceptance_criteria:
            if verification_result and verification_result.passed:
                criteria_met.append(criterion)
            else:
                criteria_pending.append(criterion)

        # Check verification
        if verification_result:
            if verification_result.passed:
                criteria_met.append("Verification passed")
            else:
                criteria_pending.append(f"Verification failed: {len(verification_result.issues)} issues")
        else:
            criteria_met.append("No verification required")

        # Check outputs
        if task_outputs:
            criteria_met.append("Task outputs produced")
        else:
            criteria_pending.append("No task outputs found")

        # Calculate completion percentage
        total = len(criteria_met) + len(criteria_pending)
        completion = (len(criteria_met) / total * 100) if total > 0 else 0.0

        is_complete = node.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED) and len(criteria_pending) == 0

        return CompletionStatus(
            scope="task",
            target_id=task_id,
            is_complete=is_complete,
            completion_percentage=round(completion, 1),
            criteria_met=criteria_met,
            criteria_pending=criteria_pending,
            blocked_by=", ".join(criteria_pending[:3]) if criteria_pending else "",
            can_proceed=is_complete or node.status != TaskStatus.FAILED,
        )

    # ------------------------------------------------------------------
    # Phase completion
    # ------------------------------------------------------------------

    def check_phase(
        self,
        phase_name: str,
        task_graph: TaskGraph,
        phase_outputs: dict[str, Any] | None = None,
    ) -> CompletionStatus:
        """Check if a phase is complete.

        Args:
            phase_name: The phase name.
            task_graph: The task graph.
            phase_outputs: Optional aggregated phase outputs.

        Returns:
            CompletionStatus for the phase.
        """
        phase_tasks = [
            node for node in task_graph.nodes.values()
            if node.phase == phase_name
        ]

        if not phase_tasks:
            return CompletionStatus(
                scope="phase",
                target_id=phase_name,
                is_complete=False,
                completion_percentage=0.0,
                criteria_pending=[f"No tasks found for phase '{phase_name}'"],
                can_proceed=False,
            )

        criteria_met: list[str] = []
        criteria_pending: list[str] = []

        # Check all tasks
        completed_tasks = sum(1 for t in phase_tasks if t.status == TaskStatus.COMPLETED)
        failed_tasks = sum(1 for t in phase_tasks if t.status == TaskStatus.FAILED)
        total_tasks = len(phase_tasks)

        if completed_tasks == total_tasks:
            criteria_met.append(f"All {total_tasks} tasks completed")
        else:
            criteria_pending.append(f"{completed_tasks}/{total_tasks} tasks completed")
            if failed_tasks > 0:
                criteria_pending.append(f"{failed_tasks} tasks failed")

        # Check verification task
        verify_tasks = [t for t in phase_tasks if t.task_id.endswith("_verify")]
        for verify_task in verify_tasks:
            if verify_task.status == TaskStatus.COMPLETED:
                criteria_met.append("Phase verification completed")
            elif verify_task.status == TaskStatus.FAILED:
                criteria_pending.append("Phase verification failed")
            else:
                criteria_pending.append("Phase verification not completed")

        # Check outputs
        if phase_outputs:
            criteria_met.append("Phase outputs produced")

        completion = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0
        is_complete = completed_tasks == total_tasks and failed_tasks == 0

        return CompletionStatus(
            scope="phase",
            target_id=phase_name,
            is_complete=is_complete,
            completion_percentage=round(completion, 1),
            criteria_met=criteria_met,
            criteria_pending=criteria_pending,
            can_proceed=is_complete,
        )

    # ------------------------------------------------------------------
    # Project completion
    # ------------------------------------------------------------------

    def check_project(
        self,
        project_id: str,
        task_graph: TaskGraph,
        phases_completed: list[str],
        contract: dict[str, Any] | None = None,
    ) -> CompletionStatus:
        """Check if a project is complete.

        Args:
            project_id: The project identifier.
            task_graph: The task graph.
            phases_completed: List of completed phase names.
            contract: Optional project contract.

        Returns:
            CompletionStatus for the project.
        """
        criteria_met: list[str] = []
        criteria_pending: list[str] = []

        # Check all phases
        all_phases = list(task_graph.phases)
        completed_count = len([p for p in all_phases if p in phases_completed])

        if completed_count == len(all_phases):
            criteria_met.append("All phases completed")
        else:
            criteria_pending.append(f"{completed_count}/{len(all_phases)} phases completed")

        # Check all tasks
        all_tasks = list(task_graph.nodes.values())
        completed_tasks = sum(1 for t in all_tasks if t.status == TaskStatus.COMPLETED)
        if completed_tasks == len(all_tasks):
            criteria_met.append("All tasks completed")
        else:
            criteria_pending.append(f"{completed_tasks}/{len(all_tasks)} tasks completed")

        # Check contract
        if contract:
            if contract.get("status") == "finalized":
                criteria_met.append("Contract finalized")
            else:
                criteria_pending.append("Contract not finalized")

        # Calculate completion
        completion = (completed_tasks / len(all_tasks) * 100) if all_tasks else 0.0
        is_complete = completed_count == len(all_phases) and completed_tasks == len(all_tasks)

        return CompletionStatus(
            scope="project",
            target_id=project_id,
            is_complete=is_complete,
            completion_percentage=round(completion, 1),
            criteria_met=criteria_met,
            criteria_pending=criteria_pending,
            can_proceed=is_complete,
        )

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(
                type=event_type, data=data, source="completion_checker",
            ))
        except Exception:
            pass
