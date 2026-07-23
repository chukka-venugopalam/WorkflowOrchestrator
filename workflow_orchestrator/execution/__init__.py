"""Execution Plane — deterministic workflow execution system.

This package contains the execution system that coordinates workflows.
The Execution Engine communicates only through interfaces — it never
knows about AI providers or specific agents.

Contains NO provider-specific code.
Contains NO AI agent logic.

Structure:
    - ``execution_context.py``: Runtime context for a single execution
    - ``workflow_compiler.py``: Compiles YAML/JSON into ExecutionGraph
    - ``workflow_validator.py``: Validates workflow definitions
    - ``workflow_loader.py``: Loads YAML/JSON workflow definitions
    - ``dependency_resolver.py``: Resolves step dependencies and ordering
    - ``execution_queue.py``: FIFO, priority, and delayed queue
    - ``retry_engine.py``: Retry policies, backoff, failure classification
    - ``step_executor.py``: Executes a single step via plugin dispatch
    - ``execution_engine.py``: Coordinates step execution with events and state
    - ``workflow_engine.py``: Top-level orchestrator for full lifecycle
"""

from __future__ import annotations

__all__ = [
    # Context
    "ExecutionContext",
    # Compiler
    "WorkflowCompiler",
    "ExecutionGraph",
    "ExecutionNode",
    "ExecutionEdge",
    # Validator
    "WorkflowValidator",
    "ValidationResult",
    # Loader
    "WorkflowLoader",
    # Dependency Resolver
    "DependencyResolver",
    "ExecutionOrder",
    "StepBatch",
    # Queue
    "ExecutionQueue",
    "QueueItem",
    "DelayedItem",
    # Retry
    "RetryEngine",
    "RetryPolicy",
    "RetryState",
    "RetryDecision",
    "ErrorClass",
    # Step Executor
    "StepExecutor",
    # Execution Engine
    "ExecutionEngine",
    # Workflow Engine
    "WorkflowEngine",
    "WorkflowRun",
]

from workflow_orchestrator.execution.execution_context import ExecutionContext
from workflow_orchestrator.execution.workflow_compiler import (
    WorkflowCompiler,
    ExecutionGraph,
    ExecutionNode,
    ExecutionEdge,
)
from workflow_orchestrator.execution.workflow_validator import (
    WorkflowValidator,
    ValidationResult,
)
from workflow_orchestrator.execution.workflow_loader import WorkflowLoader
from workflow_orchestrator.execution.dependency_resolver import (
    DependencyResolver,
    ExecutionOrder,
    StepBatch,
)
from workflow_orchestrator.execution.execution_queue import (
    ExecutionQueue,
    QueueItem,
    DelayedItem,
)
from workflow_orchestrator.execution.retry_engine import (
    RetryEngine,
    RetryPolicy,
    RetryState,
    RetryDecision,
    ErrorClass,
)
from workflow_orchestrator.execution.step_executor import StepExecutor
from workflow_orchestrator.execution.execution_engine import ExecutionEngine
from workflow_orchestrator.execution.workflow_engine import WorkflowEngine, WorkflowRun
