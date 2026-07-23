"""Autonomous Project Builder — transforms natural-language ideas into complete executable projects.

This package contains the Autonomous Project Builder, the highest-level
deterministic orchestrator that coordinates every subsystem to transform
a simple user idea (e.g., "Build a Food Delivery Platform") into a
complete executable project with architecture, workflows, tasks,
documentation, and deployment plans.

Packages:
    project_builder: Main orchestrator — coordinates every subsystem.
    project_initializer: Creates a new project, workspace, contract, session, state.
    project_classifier: Classifies project type (Web, Mobile, Desktop, CLI, AI, etc.).
    requirement_extractor: Transforms a simple user idea into structured requirements.
    architecture_generator: Creates architecture specification (not code).
    roadmap_generator: Creates implementation phases, milestones, deliverables.
    task_graph_builder: Produces a DAG of tasks with dependencies, priorities, capabilities.
    workflow_generator: Automatically converts task graph into executable workflows (YAML).
    provider_assignment: Uses Decision Engine to assign providers, agents, transports.
    execution_planner: Creates execution batches with parallel/sequential groups.
    verification_manager: Runs tests, lint, typecheck, contract/artifact/architecture validation.
    artifact_validator: Checks completeness, integrity, dependencies, content hashes.
    completion_checker: Determines task/phase/project/contract completion.
    deployment_planner: Creates deployment plans (env, hosting, secrets, CI/CD, monitoring).
    documentation_generator: Automatically updates README, CHANGELOG, ARCHITECTURE, etc.
    state_manager: Tracks project state, current phase/task, history, milestones, stats.
    resume_manager: Supports resume after restart/crash/shutdown/from checkpoint.
    rollback_manager: Creates checkpoints, supports rollback and version recovery.
    progress_tracker: Tracks completed/failed tasks, retries, duration, provider/agent usage.
    dependency_graph: Maintains project dependency graph with queries, visualization, cycle detection.
"""

from __future__ import annotations

from workflow_orchestrator.builder.project_builder import ProjectBuilder, ProjectBuilderConfig
from workflow_orchestrator.builder.project_initializer import ProjectInitializer
from workflow_orchestrator.builder.project_classifier import ProjectClassifier, ProjectType
from workflow_orchestrator.builder.requirement_extractor import RequirementExtractor
from workflow_orchestrator.builder.architecture_generator import ArchitectureGenerator
from workflow_orchestrator.builder.roadmap_generator import RoadmapGenerator
from workflow_orchestrator.builder.task_graph_builder import TaskGraphBuilder
from workflow_orchestrator.builder.workflow_generator import WorkflowGenerator
from workflow_orchestrator.builder.provider_assignment import ProviderAssignment
from workflow_orchestrator.builder.execution_planner import ExecutionPlanner
from workflow_orchestrator.builder.verification_manager import VerificationManager
from workflow_orchestrator.builder.artifact_validator import ArtifactValidator
from workflow_orchestrator.builder.completion_checker import CompletionChecker
from workflow_orchestrator.builder.deployment_planner import DeploymentPlanner
from workflow_orchestrator.builder.documentation_generator import DocumentationGenerator
from workflow_orchestrator.builder.state_manager import StateManager
from workflow_orchestrator.builder.resume_manager import ResumeManager
from workflow_orchestrator.builder.rollback_manager import RollbackManager
from workflow_orchestrator.builder.progress_tracker import ProgressTracker
from workflow_orchestrator.builder.dependency_graph import DependencyGraph
from workflow_orchestrator.builder.data_models import (
    BuilderConfig,
    ProjectState,
    PhaseState,
    TaskNode,
    TaskEdge,
    TaskGraph,
    ResourceAssignment,
    ExecutionBatch,
    VerificationResult,
    ArtifactCheckResult,
    CompletionStatus,
    DeploymentPlan,
    DocumentationSet,
    ProgressSnapshot,
    CheckpointRecord,
    RollbackResult,
)

__all__ = [
    # Main orchestrator
    "ProjectBuilder",
    "ProjectBuilderConfig",
    # Components
    "ProjectInitializer",
    "ProjectClassifier",
    "ProjectType",
    "RequirementExtractor",
    "ArchitectureGenerator",
    "RoadmapGenerator",
    "TaskGraphBuilder",
    "WorkflowGenerator",
    "ProviderAssignment",
    "ExecutionPlanner",
    "VerificationManager",
    "ArtifactValidator",
    "CompletionChecker",
    "DeploymentPlanner",
    "DocumentationGenerator",
    "StateManager",
    "ResumeManager",
    "RollbackManager",
    "ProgressTracker",
    "DependencyGraph",
    # Data models
    "BuilderConfig",
    "ProjectState",
    "PhaseState",
    "TaskNode",
    "TaskEdge",
    "TaskGraph",
    "ResourceAssignment",
    "ExecutionBatch",
    "VerificationResult",
    "ArtifactCheckResult",
    "CompletionStatus",
    "DeploymentPlan",
    "DocumentationSet",
    "ProgressSnapshot",
    "CheckpointRecord",
    "RollbackResult",
]
