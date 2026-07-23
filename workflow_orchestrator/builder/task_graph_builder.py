"""Task Graph Builder — produces a complete DAG (Directed Acyclic Graph) of tasks.

Every task contains:
- Dependencies (task IDs it depends on)
- Priority (critical, high, medium, low)
- Capabilities required
- Expected outputs
- Acceptance criteria
- Estimated complexity
- Retry policy

NOT a todo list — a proper directed acyclic graph.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from workflow_orchestrator.builder.data_models import (
    TaskEdge,
    TaskGraph,
    TaskNode,
    TaskPriority,
    TaskStatus,
)
from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class TaskGraphBuilder:
    """Builds a directed acyclic graph of tasks from roadmap phases.

    Each phase produces multiple task nodes with proper dependency
    resolution, priority assignment, and capability requirements.

    Usage:
        >>> builder = TaskGraphBuilder()
        >>> graph = builder.build(roadmap, requirements, architecture, project_id)
        >>> print(len(graph.nodes), "tasks with", len(graph.edges), "dependencies")
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Task Graph Builder.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(
        self,
        roadmap: dict[str, Any],
        requirements: dict[str, Any],
        architecture: dict[str, Any],
        project_id: str,
    ) -> TaskGraph:
        """Build a complete task graph from roadmap, requirements, and architecture.

        Args:
            roadmap: The generated roadmap.
            requirements: The structured requirements.
            architecture: The architecture specification.
            project_id: The project identifier.

        Returns:
            A TaskGraph with all task nodes and dependency edges.
        """
        graph = TaskGraph(
            graph_id=uuid.uuid4().hex[:12],
            project_id=project_id,
        )

        # Build tasks for each phase
        for phase in roadmap.get("phases", []):
            phase_num = phase.get("phase", 1)
            phase_name = phase.get("name", f"phase_{phase_num}")
            graph.phases.append(phase_name.lower().replace(" ", "_"))

            tasks = self._create_phase_tasks(phase, phase_num)
            for task in tasks:
                graph.nodes[task.task_id] = task

        # Build dependency edges
        self._build_edges(graph, roadmap)

        # Compute entry and terminal tasks
        self._compute_boundaries(graph)

        self._publish_event("builder.task_graph_built", {
            "project_id": project_id,
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
            "phase_count": len(graph.phases),
        })

        logger.info("Built task graph with %d tasks and %d edges", len(graph.nodes), len(graph.edges))
        return graph

    def _create_phase_tasks(self, phase: dict[str, Any], phase_num: int) -> list[TaskNode]:
        """Create task nodes for a single phase.

        Args:
            phase: The phase configuration dict.
            phase_num: The phase number.

        Returns:
            List of TaskNode objects.
        """
        phase_name = phase.get("name", f"phase_{phase_num}").lower().replace(" ", "_")
        tasks: list[TaskNode] = []

        # Base task: Setup
        setup_task = TaskNode(
            task_id=f"task_{phase_name}_setup",
            name=f"{phase.get('name', 'Phase')} Setup",
            description=f"Set up and prepare for {phase.get('name', 'phase')}",
            phase=phase_name,
            priority=TaskPriority.HIGH,
            status=TaskStatus.PENDING,
            capabilities_required=["reasoning.planning", "tool.filesystem"],
            expected_outputs=[f"{phase_name}_setup_complete"],
            acceptance_criteria=[f"{phase.get('name', 'Phase')} setup verified"],
            retry_policy={"max_retries": 1, "delay": 1.0},
        )
        tasks.append(setup_task)

        # Implementation tasks for each milestone
        for i, milestone in enumerate(phase.get("milestones", [])):
            milestone_name = milestone.get("name", f"milestone_{i}").lower().replace(" ", "_")
            task = TaskNode(
                task_id=f"task_{phase_name}_{milestone_name}",
                name=milestone.get("name", f"Milestone {i+1}"),
                description=f"Deliver: {', '.join(milestone.get('deliverables', []))}",
                phase=phase_name,
                priority=TaskPriority.HIGH if i == 0 else TaskPriority.MEDIUM,
                status=TaskStatus.PENDING,
                dependencies=[setup_task.task_id] if i == 0 else [setup_task.task_id, tasks[-1].task_id],
                capabilities_required=["codegen.implementation", "reasoning.problem-solving"],
                expected_outputs=milestone.get("deliverables", []),
                acceptance_criteria=[f"Milestone '{milestone.get('name', '')}' verified complete"],
                retry_policy={"max_retries": 2, "delay": 2.0},
            )
            tasks.append(task)

        # Verification task
        verify_task = TaskNode(
            task_id=f"task_{phase_name}_verify",
            name=f"Verify {phase.get('name', 'Phase')}",
            description=f"Verify all deliverables for {phase.get('name', 'phase')}",
            phase=phase_name,
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.PENDING,
            dependencies=[tasks[-1].task_id] if len(tasks) > 1 else [setup_task.task_id],
            capabilities_required=["verify.testing", "verify.lint", "verify.typecheck"],
            expected_outputs=[f"{phase_name}_verification_report"],
            acceptance_criteria=[f"Phase {phase.get('name', '')} verification passed"],
            retry_policy={"max_retries": 2, "delay": 3.0},
        )
        tasks.append(verify_task)

        return tasks

    def _build_edges(self, graph: TaskGraph, roadmap: dict[str, Any]) -> None:
        """Build dependency edges between tasks.

        Args:
            graph: The task graph to add edges to.
            roadmap: The roadmap with phase dependencies.
        """
        # Build edges based on task dependency lists
        for task_id, node in graph.nodes.items():
            for dep_id in node.dependencies:
                if dep_id in graph.nodes:
                    graph.edges.append(TaskEdge(
                        from_task_id=dep_id,
                        to_task_id=task_id,
                        type="dependency",
                    ))

        # Add cross-phase dependencies
        for phase in roadmap.get("phases", []):
            phase_num = phase.get("phase", 1)
            depends_on = phase.get("depends_on", [])
            phase_name = phase.get("name", f"phase_{phase_num}").lower().replace(" ", "_")

            for dep_phase_num in depends_on:
                dep_phase = None
                for p in roadmap.get("phases", []):
                    if p.get("phase") == dep_phase_num:
                        dep_phase = p
                        break

                if dep_phase:
                    dep_phase_name = dep_phase.get("name", f"phase_{dep_phase_num}").lower().replace(" ", "_")
                    # Connect verify of previous phase to setup of this phase
                    dep_verify_id = f"task_{dep_phase_name}_verify"
                    setup_id = f"task_{phase_name}_setup"

                    if dep_verify_id in graph.nodes and setup_id in graph.nodes:
                        graph.edges.append(TaskEdge(
                            from_task_id=dep_verify_id,
                            to_task_id=setup_id,
                            type="dependency",
                        ))

    def _compute_boundaries(self, graph: TaskGraph) -> None:
        """Compute entry and terminal tasks.

        Args:
            graph: The task graph to update.
        """
        all_dependents: set[str] = {e.to_task_id for e in graph.edges}
        all_dependencies: set[str] = {e.from_task_id for e in graph.edges}

        graph.entry_tasks = [
            tid for tid in graph.nodes
            if tid not in all_dependents
        ]
        graph.terminal_tasks = [
            tid for tid in graph.nodes
            if tid not in all_dependencies
        ]

        if not graph.edges:
            graph.entry_tasks = list(graph.nodes.keys())
            graph.terminal_tasks = list(graph.nodes.keys())

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(
                type=event_type, data=data, source="task_graph_builder",
            ))
        except Exception:
            pass
