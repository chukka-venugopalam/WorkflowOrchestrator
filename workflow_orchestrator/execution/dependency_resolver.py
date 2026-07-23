"""Dependency resolver for execution graphs.

Resolves step dependencies, computes execution ordering, detects
cycles and deadlocks, and identifies parallel execution candidates.

The resolver works with the ``ExecutionGraph`` produced by the
``WorkflowCompiler`` and produces an ordered execution plan.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

from workflow_orchestrator.execution.workflow_compiler import ExecutionGraph, ExecutionNode

logger = logging.getLogger(__name__)


@dataclass
class ExecutionOrder:
    """Computed execution order for a workflow graph.

    Attributes:
        node_ids: Ordered list of node IDs (topologically sorted).
        levels: Map of node_id -> level (parallelism level).
        parallel_groups: List of groups of node IDs that can run in parallel.
        has_cycles: Whether the graph contains cycles.
        cycle_paths: Detected cycle paths if any.
    """

    node_ids: list[str] = field(default_factory=list)
    levels: dict[str, int] = field(default_factory=dict)
    parallel_groups: list[list[str]] = field(default_factory=list)
    has_cycles: bool = False
    cycle_paths: list[list[str]] = field(default_factory=list)


@dataclass
class StepBatch:
    """A batch of ready-to-execute steps.

    Attributes:
        batch_id: Unique batch identifier.
        node_ids: Node IDs that are ready to execute.
        level: Parallelism level (0 = first batch).
        can_parallelize: Whether these steps can run in parallel.
    """

    batch_id: str = ""
    node_ids: list[str] = field(default_factory=list)
    level: int = 0
    can_parallelize: bool = True


class DependencyResolver:
    """Resolves dependencies in an execution graph.

    Supports:
    - Topological sort for execution ordering
    - Cycle detection
    - Deadlock detection
    - Parallel group identification
    - Ready batch computation (next ready steps)

    Usage:
        >>> resolver = DependencyResolver()
        >>> order = resolver.resolve(graph)
        >>> print(order.node_ids)
        ['step_1', 'step_2', 'step_3']
        >>> batch = resolver.next_ready_batch(graph, completed=set())
        >>> print(batch.node_ids)
        ['step_1']
    """

    # ------------------------------------------------------------------
    # Main resolution
    # ------------------------------------------------------------------

    def resolve(self, graph: ExecutionGraph) -> ExecutionOrder:
        """Resolve the execution order for a graph.

        Performs topological sort, cycle detection, and level assignment.

        Args:
            graph: The execution graph to resolve.

        Returns:
            An ExecutionOrder with sorted nodes and parallelism info.
        """
        # Build adjacency list
        in_degree: dict[str, int] = {nid: 0 for nid in graph.nodes}
        adjacency: dict[str, list[str]] = {nid: [] for nid in graph.nodes}

        for edge in graph.edges:
            if edge.to_node_id in in_degree:
                in_degree[edge.to_node_id] = in_degree.get(edge.to_node_id, 0) + 1
            if edge.from_node_id in adjacency:
                adjacency[edge.from_node_id].append(edge.to_node_id)

        # Detect cycles using DFS
        has_cycles, cycle_paths = self._detect_cycles(graph)
        if has_cycles:
            logger.error("Cycle detected in workflow graph: %s", cycle_paths)
            return ExecutionOrder(
                has_cycles=True,
                cycle_paths=cycle_paths,
            )

        # Topological sort using Kahn's algorithm
        queue: deque[str] = deque()
        for nid in graph.nodes:
            if in_degree.get(nid, 0) == 0:
                queue.append(nid)

        sorted_nodes: list[str] = []
        levels: dict[str, int] = {}

        while queue:
            node_id = queue.popleft()
            sorted_nodes.append(node_id)

            # Assign level based on max predecessor level + 1
            pred_levels = [
                levels.get(e.from_node_id, -1)
                for e in graph.edges
                if e.to_node_id == node_id
            ]
            levels[node_id] = max(pred_levels, default=-1) + 1

            for neighbor in adjacency.get(node_id, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Build parallel groups (same level = same group)
        level_groups: dict[int, list[str]] = {}
        for nid, level in levels.items():
            level_groups.setdefault(level, []).append(nid)

        parallel_groups = [
            level_groups[level]
            for level in sorted(level_groups.keys())
        ]

        logger.debug(
            "Resolved execution order: %d nodes, %d levels, %d parallel groups",
            len(sorted_nodes),
            len(levels),
            len(parallel_groups),
        )
        return ExecutionOrder(
            node_ids=sorted_nodes,
            levels=levels,
            parallel_groups=parallel_groups,
        )

    # ------------------------------------------------------------------
    # Ready batch computation
    # ------------------------------------------------------------------

    def next_ready_batch(
        self,
        graph: ExecutionGraph,
        completed: set[str],
        failed: set[str] | None = None,
    ) -> StepBatch:
        """Compute the next batch of ready-to-execute steps.

        A step is ready when all its dependencies have been completed.

        Args:
            graph: The execution graph.
            completed: Set of already-completed node IDs.
            failed: Set of failed node IDs (optional).

        Returns:
            A StepBatch of ready nodes.
        """
        failed = failed or set()
        ready: list[str] = []

        for nid, node in graph.nodes.items():
            if nid in completed or nid in failed:
                continue
            if node.status in ("running", "completed"):
                continue

            # All dependencies must be completed
            deps = {e.from_node_id for e in graph.edges if e.to_node_id == nid}
            if deps and not deps.issubset(completed):
                continue

            ready.append(nid)

        # Determine if these can be parallelized
        can_parallelize = len(ready) > 1

        import uuid
        batch = StepBatch(
            batch_id=uuid.uuid4().hex[:8],
            node_ids=ready,
            can_parallelize=can_parallelize,
        )

        if ready:
            logger.debug("Ready batch: %s", ready)
        return batch

    # ------------------------------------------------------------------
    # Cycle detection
    # ------------------------------------------------------------------

    def _detect_cycles(
        self,
        graph: ExecutionGraph,
    ) -> tuple[bool, list[list[str]]]:
        """Detect cycles in the execution graph using DFS.

        Args:
            graph: The execution graph.

        Returns:
            Tuple of (has_cycles, cycle_paths).
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {nid: WHITE for nid in graph.nodes}
        parent: dict[str, str | None] = {nid: None for nid in graph.nodes}
        cycles: list[list[str]] = []

        # Build adjacency
        adj: dict[str, list[str]] = {nid: [] for nid in graph.nodes}
        for edge in graph.edges:
            if edge.from_node_id in adj:
                adj[edge.from_node_id].append(edge.to_node_id)

        def dfs(node: str) -> None:
            color[node] = GRAY
            for neighbor in adj.get(node, []):
                if color.get(neighbor) == GRAY:
                    # Found a cycle — reconstruct the path
                    cycle = [neighbor, node]
                    current = node
                    while current != neighbor and parent.get(current) is not None:
                        current = parent[current]  # type: ignore[assignment]
                        if current:
                            cycle.append(current)
                    cycles.append(list(reversed(cycle)))
                elif color.get(neighbor) == WHITE:
                    parent[neighbor] = node
                    dfs(neighbor)
            color[node] = BLACK

        for nid in graph.nodes:
            if color.get(nid) == WHITE:
                dfs(nid)

        return len(cycles) > 0, cycles

    # ------------------------------------------------------------------
    # Conflict detection
    # ------------------------------------------------------------------

    def conflicts(
        self,
        graph: ExecutionGraph,
        step_ids: list[str],
    ) -> list[dict[str, Any]]:
        """Detect conflicts between steps.

        Currently checks write-scope overlap between steps.
        Future versions will check resource conflicts.

        Args:
            graph: The execution graph.
            step_ids: Step IDs to check for conflicts.

        Returns:
            List of conflict reports.
        """
        conflicts_list: list[dict[str, Any]] = []

        for i, nid_a in enumerate(step_ids):
            for nid_b in step_ids[i + 1:]:
                node_a = graph.nodes.get(nid_a)
                node_b = graph.nodes.get(nid_b)
                if not node_a or not node_b:
                    continue

                # Check if both write to the same output
                output_a = node_a.config.get("output", node_a.config.get("write_to", ""))
                output_b = node_b.config.get("output", node_b.config.get("write_to", ""))

                if output_a and output_b and output_a == output_b:
                    conflicts_list.append({
                        "type": "write_scope_conflict",
                        "nodes": [nid_a, nid_b],
                        "resource": output_a,
                        "message": f"Both '{nid_a}' and '{nid_b}' write to '{output_a}'",
                    })

        return conflicts_list

    def has_conflicts(self, graph: ExecutionGraph, step_ids: list[str]) -> bool:
        """Quick check if there are any conflicts between steps.

        Args:
            graph: The execution graph.
            step_ids: Step IDs to check.

        Returns:
            True if any conflicts exist.
        """
        return len(self.conflicts(graph, step_ids)) > 0
