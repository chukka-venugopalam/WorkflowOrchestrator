"""Execution Planner — creates execution batches with parallel/sequential groups, approval gates, verification points, and checkpoint schedules.

Takes the task graph and produces ordered execution batches optimized
for parallel execution where possible while respecting dependencies.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from workflow_orchestrator.builder.data_models import (
    ExecutionBatch,
    TaskGraph,
    TaskNode,
    TaskStatus,
)
from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class ExecutionPlanner:
    """Creates execution batches from a task graph.

    Groups tasks into execution batches that can be run in parallel
    or sequentially, with proper ordering based on the dependency graph.

    Usage:
        >>> planner = ExecutionPlanner()
        >>> batches = planner.plan(graph, assignments, max_concurrent=3)
        >>> print(len(batches), "execution batches")
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Execution Planner.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------

    def plan(
        self,
        task_graph: TaskGraph,
        assignments: list[Any] | None = None,
        max_concurrent: int = 3,
    ) -> list[ExecutionBatch]:
        """Create execution batches from the task graph.

        Uses topological ordering to group tasks into batches where
        tasks in the same batch can run in parallel (no inter-dependencies).

        Args:
            task_graph: The task graph to plan execution for.
            assignments: Optional resource assignments.
            max_concurrent: Maximum number of parallel tasks per batch.

        Returns:
            Ordered list of ExecutionBatch objects.
        """
        # Build dependency tracking
        completed: set[str] = set()
        remaining: set[str] = set(task_graph.nodes.keys())
        batches: list[ExecutionBatch] = []

        batch_index = 0

        while remaining:
            # Find tasks with all dependencies completed
            ready = self._find_ready_tasks(remaining, task_graph, completed)

            if not ready:
                # Circular dependency or blocking issue
                logger.warning("No ready tasks found — possible circular dependency")
                # Force-add remaining tasks to break deadlock
                ready = list(remaining)

            # Create batches from ready tasks, respecting max_concurrent
            batched_ready = [
                ready[i:i + max_concurrent]
                for i in range(0, len(ready), max_concurrent)
            ]

            for batch_tasks in batched_ready:
                batch_index += 1
                is_parallel = len(batch_tasks) > 1

                batch = ExecutionBatch(
                    batch_id=f"batch_{batch_index:03d}",
                    tasks=batch_tasks,
                    mode="parallel" if is_parallel else "sequential",
                    approval_required=False,
                    verification_points=[],
                    checkpoint_after=(batch_index % 5 == 0),
                )

                # Add verification point for last batch in phase
                if any(self._is_phase_terminal(tid, task_graph) for tid in batch_tasks):
                    task = next(task_graph.nodes[tid] for tid in batch_tasks if self._is_phase_terminal(tid, task_graph))
                    batch.verification_points = [f"Verify phase: {task.phase}"]

                batches.append(batch)

                # Mark tasks as completed for next iteration
                for tid in batch_tasks:
                    completed.add(tid)
                    remaining.discard(tid)

        # Mark approval gates
        self._mark_approval_gates(batches, task_graph)

        self._publish_event("builder.execution_planned", {
            "batch_count": len(batches),
            "total_tasks": sum(len(b.tasks) for b in batches),
            "parallel_batches": sum(1 for b in batches if b.mode == "parallel"),
        })

        logger.info("Planned %d execution batches (%d parallel)", len(batches), sum(1 for b in batches if b.mode == "parallel"))
        return batches

    def _find_ready_tasks(
        self,
        remaining: set[str],
        graph: TaskGraph,
        completed: set[str],
    ) -> list[str]:
        """Find tasks whose dependencies are all completed.

        Args:
            remaining: Set of remaining task IDs.
            graph: The task graph.
            completed: Set of completed task IDs.

        Returns:
            List of task IDs ready for execution.
        """
        ready: list[str] = []

        for task_id in remaining:
            node = graph.nodes[task_id]
            deps_met = all(dep in completed for dep in node.dependencies)
            if deps_met:
                ready.append(task_id)

        # Sort by priority then phase
        def _sort_key(tid: str) -> tuple[int, str]:
            node = graph.nodes[tid]
            priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            return (priority_order.get(node.priority.value, 99), node.phase)

        ready.sort(key=_sort_key)
        return ready

    def _is_phase_terminal(self, task_id: str, graph: TaskGraph) -> bool:
        """Check if a task is the terminal task in its phase.

        Args:
            task_id: The task identifier.
            graph: The task graph.

        Returns:
            True if this is the last task in its phase.
        """
        node = graph.nodes.get(task_id)
        if node is None:
            return False

        phase = node.phase
        phase_tasks = [t for t in graph.nodes.values() if t.phase == phase]
        # The verify task is the terminal task
        return task_id.endswith("_verify")

    def _mark_approval_gates(self, batches: list[ExecutionBatch], graph: TaskGraph) -> None:
        """Mark batches that require human approval.

        Args:
            batches: The execution batches.
            graph: The task graph.
        """
        for i, batch in enumerate(batches):
            for task_id in batch.tasks:
                node = graph.nodes.get(task_id)
                if node and node.name.startswith("Verify"):
                    # Verification tasks might need approval before proceeding
                    batch.approval_required = True
                    break

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(
                type=event_type, data=data, source="execution_planner",
            ))
        except Exception:
            pass
