"""Dependency Graph — maintains the project dependency graph.

Supports:
- Queries
- Visualization (ASCII tree)
- Cycle detection
- Impact analysis (what is affected by changes)
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from typing import Any, Optional

from workflow_orchestrator.builder.data_models import TaskEdge, TaskGraph, TaskNode
from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class DependencyGraph:
    """Maintains and queries the project task dependency graph.

    Provides cycle detection, topological ordering, impact analysis,
    and ASCII visualization of the dependency graph.

    Usage:
        >>> dg = DependencyGraph()
        >>> dg.load(task_graph)
        >>> if dg.has_cycles():
        ...     print("Cycles found:", dg.find_cycles())
        >>> affected = dg.impact_analysis("task_001")
        >>> print(dg.render_ascii())
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Dependency Graph.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus
        self._graph: dict[str, set[str]] = {}  # task_id -> set of dependencies
        self._reverse: dict[str, set[str]] = {}  # task_id -> set of dependents
        self._nodes: dict[str, TaskNode] = {}
        self._node_names: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self, task_graph: TaskGraph) -> None:
        """Load a task graph into the dependency graph.

        Args:
            task_graph: The task graph to load.
        """
        self._graph.clear()
        self._reverse.clear()
        self._nodes.clear()
        self._node_names.clear()

        for task_id, node in task_graph.nodes.items():
            self._graph[task_id] = set(node.dependencies)
            self._reverse[task_id] = set()
            self._nodes[task_id] = node
            self._node_names[task_id] = node.name

        # Build reverse dependency map
        for task_id, deps in self._graph.items():
            for dep_id in deps:
                if dep_id in self._reverse:
                    self._reverse[dep_id].add(task_id)

        logger.debug("Loaded %d nodes into dependency graph", len(self._nodes))

    def add_node(self, node: TaskNode) -> None:
        """Add a node to the dependency graph.

        Args:
            node: The task node to add.
        """
        if node.task_id not in self._graph:
            self._graph[node.task_id] = set(node.dependencies)
            self._reverse[node.task_id] = set()
            self._nodes[node.task_id] = node
            self._node_names[node.task_id] = node.name

            # Update reverse deps
            for dep_id in node.dependencies:
                if dep_id in self._reverse:
                    self._reverse[dep_id].add(node.task_id)

    def remove_node(self, task_id: str) -> None:
        """Remove a node and its edges from the graph.

        Args:
            task_id: The task to remove.
        """
        if task_id not in self._graph:
            return

        # Remove from reverse dependencies
        for dep_id in self._graph[task_id]:
            if dep_id in self._reverse:
                self._reverse[dep_id].discard(task_id)

        # Remove from forward dependencies
        for dependent_id in self._reverse.get(task_id, set()):
            if dependent_id in self._graph:
                self._graph[dependent_id].discard(task_id)

        del self._graph[task_id]
        self._reverse.pop(task_id, None)
        self._nodes.pop(task_id, None)
        self._node_names.pop(task_id, None)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_dependencies(self, task_id: str) -> list[str]:
        """Get the direct dependencies of a task.

        Args:
            task_id: The task identifier.

        Returns:
            List of dependency task IDs.
        """
        return list(self._graph.get(task_id, set()))

    def get_dependents(self, task_id: str) -> list[str]:
        """Get the direct dependents of a task (tasks that depend on it).

        Args:
            task_id: The task identifier.

        Returns:
            List of dependent task IDs.
        """
        return list(self._reverse.get(task_id, set()))

    def get_all_dependencies(self, task_id: str) -> set[str]:
        """Get all transitive dependencies of a task (ancestors).

        Args:
            task_id: The task identifier.

        Returns:
            Set of all ancestor task IDs.
        """
        visited: set[str] = set()
        queue: deque[str] = deque([task_id])

        while queue:
            current = queue.popleft()
            for dep_id in self._graph.get(current, set()):
                if dep_id not in visited:
                    visited.add(dep_id)
                    queue.append(dep_id)

        visited.discard(task_id)
        return visited

    def get_all_dependents(self, task_id: str) -> set[str]:
        """Get all transitive dependents of a task (descendants).

        Args:
            task_id: The task identifier.

        Returns:
            Set of all descendant task IDs.
        """
        visited: set[str] = set()
        queue: deque[str] = deque([task_id])

        while queue:
            current = queue.popleft()
            for dependent_id in self._reverse.get(current, set()):
                if dependent_id not in visited:
                    visited.add(dependent_id)
                    queue.append(dependent_id)

        visited.discard(task_id)
        return visited

    def get_path(self, from_task: str, to_task: str) -> list[str]:
        """Find a dependency path between two tasks.

        Args:
            from_task: The source task.
            to_task: The target task.

        Returns:
            List of task IDs forming a path, or empty list if no path exists.
        """
        visited: set[str] = set()
        queue: deque[tuple[str, list[str]]] = deque([(from_task, [from_task])])

        while queue:
            current, path = queue.popleft()
            if current == to_task:
                return path

            for dep_id in self._graph.get(current, set()):
                if dep_id not in visited:
                    visited.add(dep_id)
                    queue.append((dep_id, path + [dep_id]))

            for dependent_id in self._reverse.get(current, set()):
                if dependent_id not in visited:
                    visited.add(dependent_id)
                    queue.append((dependent_id, path + [dependent_id]))

        return []

    # ------------------------------------------------------------------
    # Topological ordering
    # ------------------------------------------------------------------

    def topological_sort(self) -> list[str]:
        """Get tasks in topological order (dependencies first).

        Returns:
            List of task IDs in topological order.

        Raises:
            ValueError: If the graph contains cycles.
        """
        in_degree: dict[str, int] = {}
        for task_id in self._graph:
            in_degree[task_id] = len(self._graph[task_id])

        queue: deque[str] = deque(
            tid for tid, deg in in_degree.items() if deg == 0
        )

        result: list[str] = []
        while queue:
            current = queue.popleft()
            result.append(current)

            for dependent_id in self._reverse.get(current, set()):
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)

        if len(result) != len(self._graph):
            raise ValueError("Graph contains cycles, topological sort impossible")

        return result

    # ------------------------------------------------------------------
    # Cycle detection
    # ------------------------------------------------------------------

    def has_cycles(self) -> bool:
        """Check if the graph contains cycles.

        Returns:
            True if cycles exist.
        """
        try:
            self.topological_sort()
            return False
        except ValueError:
            return True

    def find_cycles(self) -> list[list[str]]:
        """Find all cycles in the graph.

        Returns:
            List of cycles, each cycle is a list of task IDs.
        """
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()
        parent: dict[str, str | None] = {}

        def dfs(node: str) -> None:
            """Depth-first search for cycle detection.

            Args:
                node: Current node.
            """
            visited.add(node)
            rec_stack.add(node)

            for dep_id in self._graph.get(node, set()):
                if dep_id not in visited:
                    parent[dep_id] = node
                    dfs(dep_id)
                elif dep_id in rec_stack:
                    # Found a cycle
                    cycle: list[str] = []
                    current = node
                    while current != dep_id and current is not None:
                        cycle.append(current)
                        current = parent.get(current, None)  # type: ignore[arg-type]
                        if current is None:
                            break
                    cycle.append(dep_id)
                    cycle.append(node)
                    cycle.reverse()
                    cycles.append(cycle)

            rec_stack.discard(node)

        for task_id in self._graph:
            if task_id not in visited:
                dfs(task_id)

        return cycles

    # ------------------------------------------------------------------
    # Impact analysis
    # ------------------------------------------------------------------

    def impact_analysis(self, task_id: str) -> dict[str, Any]:
        """Analyze the impact of changing or removing a task.

        Args:
            task_id: The task to analyze.

        Returns:
            Dict with impact analysis results.
        """
        dependents = self.get_all_dependents(task_id)
        dependencies = self.get_all_dependencies(task_id)

        # Determine impact level
        if not dependents:
            impact_level = "low"
        elif len(dependents) <= 3:
            impact_level = "medium"
        else:
            impact_level = "high"

        return {
            "task_id": task_id,
            "task_name": self._node_names.get(task_id, task_id),
            "impact_level": impact_level,
            "direct_dependents": self.get_dependents(task_id),
            "all_dependents": list(dependents),
            "all_dependencies": list(dependencies),
            "total_affected": len(dependents),
            "has_cycles": self.has_cycles(),
        }

    def critical_path(self) -> list[str]:
        """Find the critical path (longest dependency chain).

        Returns:
            List of task IDs on the critical path.
        """
        # Find nodes with no dependencies (entry points)
        entry_nodes = [tid for tid in self._graph if not self._graph[tid]]
        if not entry_nodes:
            return []

        # Compute longest path from each entry node
        memo: dict[str, list[str]] = {}

        def longest_path(node: str) -> list[str]:
            """Compute the longest path from a node.

            Args:
                node: Starting node.

            Returns:
                List of task IDs on the longest path.
            """
            if node in memo:
                return memo[node]

            best_path: list[str] = [node]
            for dependent_id in self._reverse.get(node, set()):
                path = [node] + longest_path(dependent_id)
                if len(path) > len(best_path):
                    best_path = path

            memo[node] = best_path
            return best_path

        # Find the overall longest path
        critical: list[str] = []
        for entry in entry_nodes:
            path = longest_path(entry)
            if len(path) > len(critical):
                critical = path

        return critical

    # ------------------------------------------------------------------
    # Visualization
    # ------------------------------------------------------------------

    def render_ascii(self, task_ids: list[str] | None = None) -> str:
        """Render the dependency graph as an ASCII tree.

        Args:
            task_ids: Optional subset of task IDs to render.

        Returns:
            ASCII string representation of the graph.
        """
        nodes_to_render = task_ids or list(self._graph.keys())
        if not nodes_to_render:
            return "(empty graph)"

        lines: list[str] = []
        entry_nodes = [tid for tid in nodes_to_render if tid in self._graph and not self._graph[tid]]

        if not entry_nodes:
            entry_nodes = [nodes_to_render[0]]

        def render_node(node_id: str, prefix: str = "", is_last: bool = True, visited: set[str] | None = None) -> None:
            """Render a node and its dependents recursively.

            Args:
                node_id: The node to render.
                prefix: Current line prefix.
                is_last: Whether this is the last sibling.
                visited: Set of visited nodes to prevent infinite recursion.
            """
            if visited is None:
                visited = set()

            if node_id in visited:
                lines.append(f"{prefix}{'└── ' if is_last else '├── '}{node_id} (*cycle*)")
                return

            visited.add(node_id)
            name = self._node_names.get(node_id, node_id)
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{name} ({node_id[:8]})")

            dependents = [d for d in self._reverse.get(node_id, set()) if d in nodes_to_render]
            new_prefix = prefix + ("    " if is_last else "│   ")

            for i, dep_id in enumerate(dependents):
                is_last_dep = i == len(dependents) - 1
                render_node(dep_id, new_prefix, is_last_dep, visited.copy())

        for i, entry in enumerate(entry_nodes):
            is_last_entry = i == len(entry_nodes) - 1
            render_node(entry, "", is_last_entry)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def node_count(self) -> int:
        """Number of nodes in the graph."""
        return len(self._graph)

    @property
    def edge_count(self) -> int:
        """Number of edges in the graph."""
        return sum(len(deps) for deps in self._graph.values())

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(
                type=event_type, data=data, source="dependency_graph",
            ))
        except Exception:
            pass
