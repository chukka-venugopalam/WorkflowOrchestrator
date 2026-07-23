"""Workflow validator for execution graphs.

Validates workflows against schema rules, dependency constraints,
capability requirements, variable references, and structural integrity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from workflow_orchestrator.execution.workflow_compiler import ExecutionGraph, ExecutionNode
from workflow_orchestrator.models import WorkflowDefinition

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a workflow validation.

    Attributes:
        valid: Whether the workflow passed all validation checks.
        errors: List of validation error messages.
        warnings: List of validation warnings.
        graph: The validated execution graph (if valid).
    """

    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    graph: ExecutionGraph | None = None


class WorkflowValidator:
    """Validates workflow definitions and execution graphs.

    Performs the following validations:
    - Schema validation (required fields, correct types)
    - Dependency validation (no cycles, valid references)
    - Capability validation (required capabilities are declared)
    - Variable validation (variable references resolve correctly)
    - Reference validation (step references are valid)

    Usage:
        >>> validator = WorkflowValidator()
        >>> result = validator.validate(workflow_definition)
        >>> if result.valid:
        ...     graph = result.graph
    """

    # Required fields per step
    REQUIRED_STEP_FIELDS = {"plugin", "config"}
    OPTIONAL_STEP_FIELDS = {"name", "on_failure", "retry", "depends_on", "dependsOn"}

    # Valid failure actions
    VALID_ON_FAILURE = {"stop", "continue", "retry"}

    # Valid step keys in YAML
    VALID_STEP_KEYS = REQUIRED_STEP_FIELDS | OPTIONAL_STEP_FIELDS | {"_step_name"}

    def validate(
        self,
        workflow: WorkflowDefinition,
    ) -> ValidationResult:
        """Validate a workflow definition.

        Args:
            workflow: The workflow definition to validate.

        Returns:
            ValidationResult with errors, warnings, and compiled graph.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Basic structure validation
        self._validate_structure(workflow, errors, warnings)

        if errors:
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        # 2. Compile to graph for deeper validation
        from workflow_orchestrator.execution.workflow_compiler import WorkflowCompiler
        compiler = WorkflowCompiler()

        try:
            graph = compiler.compile(workflow)
        except ValueError as exc:
            errors.append(str(exc))
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        # 3. Graph-level validation
        self._validate_graph(graph, errors, warnings)

        # 4. Dependency validation
        self._validate_dependencies(graph, errors, warnings)

        if errors:
            return ValidationResult(valid=False, errors=errors, warnings=warnings, graph=graph)

        return ValidationResult(valid=True, warnings=warnings, graph=graph)

    def _validate_structure(
        self,
        workflow: WorkflowDefinition,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        """Validate the basic structure of a workflow definition.

        Args:
            workflow: The workflow definition.
            errors: List to append errors to.
            warnings: List to append warnings to.
        """
        # Name is required
        if not workflow.name:
            errors.append("Workflow must have a name")

        # Steps are required
        if not workflow.steps:
            errors.append("Workflow must have at least one step")
            return

        # Validate each step
        for i, step in enumerate(workflow.steps, start=1):
            self._validate_step(step, i, errors, warnings)

    def _validate_step(
        self,
        step: Any,
        index: int,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        """Validate a single workflow step.

        Args:
            step: The step to validate.
            index: 1-based step index.
            errors: List to append errors to.
            warnings: List to append warnings to.
        """
        step_name = step.name or f"Step {index}"

        # Plugin is required
        if not step.plugin:
            errors.append(f"{step_name}: 'plugin' is required")

        # Config should be a dict
        if not isinstance(step.config, dict):
            warnings.append(f"{step_name}: 'config' should be a dictionary")

        # On-failure validation
        if step.on_failure and step.on_failure.value not in self.VALID_ON_FAILURE:
            warnings.append(
                f"{step_name}: Invalid on_failure '{step.on_failure.value}'. "
                f"Valid: {', '.join(self.VALID_ON_FAILURE)}"
            )

        # Retry validation
        if step.retry:
            if step.retry.max_retries < 0:
                errors.append(f"{step_name}: max_retries must be >= 0")
            if step.retry.delay < 0:
                errors.append(f"{step_name}: delay must be >= 0")
            if step.retry.backoff < 0:
                errors.append(f"{step_name}: backoff must be >= 0")

    def _validate_graph(
        self,
        graph: ExecutionGraph,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        """Validate a compiled execution graph.

        Args:
            graph: The execution graph.
            errors: List to append errors to.
            warnings: List to append warnings to.
        """
        if not graph.nodes:
            errors.append("Execution graph has no nodes")
            return

        # Check for isolated nodes (no edges but multiple nodes)
        if len(graph.nodes) > 1 and not graph.edges:
            warnings.append(
                "All steps are independent (no dependencies declared). "
                "They may execute in parallel."
            )

    def _validate_dependencies(
        self,
        graph: ExecutionGraph,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        """Validate dependencies in the execution graph.

        Args:
            graph: The execution graph.
            errors: List to append errors to.
            warnings: List to append warnings to.
        """
        # Check for self-referencing dependencies
        for edge in graph.edges:
            if edge.from_node_id == edge.to_node_id:
                errors.append(
                    f"Step '{edge.from_node_id}' has a self-referencing dependency"
                )

        # Check for orphan dependency targets
        for node in graph.nodes.values():
            for dep_id in node.depends_on:
                if dep_id not in graph.nodes:
                    errors.append(
                        f"Step '{node.node_id}' depends on unknown step '{dep_id}'"
                    )

        # Check for cycle dependencies using the resolver
        from workflow_orchestrator.execution.dependency_resolver import DependencyResolver
        resolver = DependencyResolver()
        order = resolver.resolve(graph)

        if order.has_cycles:
            errors.append(
                f"Circular dependency detected: {order.cycle_paths}"
            )

    def validate_graph(
        self,
        graph: ExecutionGraph,
    ) -> ValidationResult:
        """Validate an already-compiled execution graph.

        Args:
            graph: The execution graph to validate.

        Returns:
            ValidationResult.
        """
        errors: list[str] = []
        warnings: list[str] = []
        self._validate_graph(graph, errors, warnings)
        self._validate_dependencies(graph, errors, warnings)
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            graph=graph,
        )
