"""Workflow compiler — transforms YAML/JSON workflow definitions into an internal execution graph.

Output:
- ``ExecutionGraph`` — the complete directed graph representation
- ``ExecutionNode`` — a single step node with metadata
- ``ExecutionEdge`` — a dependency edge between nodes

The compiler is the bridge between the declarative workflow format
(YAML/JSON) and the imperative execution model (graph of nodes).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.models import WorkflowDefinition, WorkflowStep

logger = logging.getLogger(__name__)


@dataclass
class ExecutionNode:
    """A single node in the execution graph representing a workflow step.

    Attributes:
        node_id: Unique node identifier (auto-generated).
        step_index: 1-based step index in the original workflow.
        name: Human-readable step name.
        plugin: Plugin identifier for execution.
        config: Plugin-specific configuration.
        status: Current execution status.
        depends_on: List of node IDs this node depends on.
        retry_config: Retry configuration.
        on_failure: Failure action (``stop``, ``continue``, ``retry``).
        metadata: Additional metadata.
    """

    node_id: str = ""
    step_index: int = 0
    name: str = ""
    plugin: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    depends_on: list[str] = field(default_factory=list)
    retry_config: dict[str, Any] = field(default_factory=dict)
    on_failure: str = "stop"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionEdge:
    """A directed dependency edge between two execution nodes.

    Attributes:
        from_node_id: The source node (must complete first).
        to_node_id: The target node (depends on source).
        type: Edge type (``dependency``, ``data-flow``).
    """

    from_node_id: str
    to_node_id: str
    type: str = "dependency"


@dataclass
class ExecutionGraph:
    """Complete directed graph representation of a workflow.

    Attributes:
        workflow_id: Unique workflow identifier.
        workflow_name: Human-readable workflow name.
        description: Workflow description.
        nodes: Map of node_id -> ExecutionNode.
        edges: List of execution edges.
        entry_nodes: Node IDs with no dependencies (start here).
        terminal_nodes: Node IDs with no dependents (end here).
        metadata: Additional graph metadata.
    """

    workflow_id: str = ""
    workflow_name: str = ""
    description: str = ""
    nodes: dict[str, ExecutionNode] = field(default_factory=dict)
    edges: list[ExecutionEdge] = field(default_factory=list)
    entry_nodes: list[str] = field(default_factory=list)
    terminal_nodes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkflowCompiler:
    """Compiles workflow definitions into executable execution graphs.

    The compilation process:
    1. Extract steps from the workflow definition
    2. Create execution nodes for each step
    3. Resolve dependencies between steps
    4. Build edges and compute entry/terminal nodes
    5. Return the complete ExecutionGraph

    Usage:
        >>> compiler = WorkflowCompiler()
        >>> graph = compiler.compile(workflow_definition)
        >>> print(len(graph.nodes))
        3
    """

    def compile(
        self,
        workflow: WorkflowDefinition,
        workflow_id: str | None = None,
    ) -> ExecutionGraph:
        """Compile a workflow definition into an execution graph.

        Args:
            workflow: The workflow definition to compile.
            workflow_id: Optional explicit workflow ID.

        Returns:
            An ExecutionGraph ready for execution.

        Raises:
            ValueError: If the workflow has no steps.
        """
        if not workflow.steps:
            raise ValueError(f"Workflow '{workflow.name}' has no steps.")

        wid = workflow_id or uuid.uuid4().hex[:12]
        graph = ExecutionGraph(
            workflow_id=wid,
            workflow_name=workflow.name,
            description=workflow.description,
            metadata={"source": workflow.source, "tags": workflow.tags},
        )

        # Step 1: Create nodes
        for i, step in enumerate(workflow.steps, start=1):
            node_id = f"step_{i}"
            depends_on: list[str] = []

            # Parse explicit dependencies from step config
            raw_deps = step.config.get("depends_on", step.config.get("dependsOn", []))
            if isinstance(raw_deps, str):
                raw_deps = [raw_deps]

            # Resolve dependency references to node IDs
            for dep in raw_deps:
                if dep.startswith("step_"):
                    depends_on.append(dep)
                else:
                    # Try to resolve by step name or index
                    resolved = self._resolve_dependency(dep, workflow.steps)
                    if resolved:
                        depends_on.append(resolved)
                    else:
                        logger.warning(
                            "Unresolved dependency '%s' in step %d of '%s'",
                            dep, i, workflow.name,
                        )

            node = ExecutionNode(
                node_id=node_id,
                step_index=i,
                name=step.name or f"{step.plugin}:{i}",
                plugin=step.plugin,
                config=step.config,
                status="pending",
                depends_on=depends_on,
                retry_config={
                    "max_retries": step.retry.max_retries,
                    "delay": step.retry.delay,
                    "backoff": step.retry.backoff,
                },
                on_failure=step.on_failure.value,
            )
            graph.nodes[node_id] = node

        # Step 2: Build edges
        for node in graph.nodes.values():
            for dep_id in node.depends_on:
                if dep_id in graph.nodes:
                    graph.edges.append(ExecutionEdge(
                        from_node_id=dep_id,
                        to_node_id=node.node_id,
                    ))

        # Step 3: Compute entry and terminal nodes
        all_dependents: set[str] = {e.to_node_id for e in graph.edges}
        all_dependencies: set[str] = {e.from_node_id for e in graph.edges}

        graph.entry_nodes = [
            nid for nid in graph.nodes
            if nid not in all_dependents
        ]
        graph.terminal_nodes = [
            nid for nid in graph.nodes
            if nid not in all_dependencies
        ]

        # If no dependencies, all nodes are both entry and terminal
        if not graph.edges:
            graph.entry_nodes = list(graph.nodes.keys())
            graph.terminal_nodes = list(graph.nodes.keys())

        logger.debug(
            "Compiled workflow '%s': %d nodes, %d edges, %d entry, %d terminal",
            workflow.name,
            len(graph.nodes),
            len(graph.edges),
            len(graph.entry_nodes),
            len(graph.terminal_nodes),
        )
        return graph

    def _resolve_dependency(self, dep: str, steps: list[WorkflowStep]) -> str | None:
        """Resolve a dependency reference to a node ID.

        Args:
            dep: Dependency reference (step name or "step_N").
            steps: List of workflow steps.

        Returns:
            Node ID or None if not resolvable.
        """
        # Check by step name
        for i, step in enumerate(steps, start=1):
            if step.name == dep:
                return f"step_{i}"

        # Check by plugin name reference
        for i, step in enumerate(steps, start=1):
            if step.plugin == dep:
                return f"step_{i}"

        return None

    def compile_from_yaml(
        self,
        yaml_path: Path | str,
        workflow_id: str | None = None,
    ) -> ExecutionGraph:
        """Load a YAML workflow and compile it.

        Args:
            yaml_path: Path to the YAML file.
            workflow_id: Optional explicit workflow ID.

        Returns:
            An ExecutionGraph.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        path = Path(yaml_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Workflow file not found: {path}")

        workflow = WorkflowDefinition.from_yaml(path)
        return self.compile(workflow, workflow_id=workflow_id)
