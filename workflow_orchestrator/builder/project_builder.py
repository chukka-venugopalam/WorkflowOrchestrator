"""Project Builder — the main orchestrator for autonomous project building.

Coordinates every subsystem:
1. ProjectInitializer — create project, workspace, contract, session, state
2. ProjectClassifier — classify project type
3. RequirementExtractor — extract structured requirements
4. ArchitectureGenerator — generate architecture specification
5. RoadmapGenerator — generate implementation roadmap
6. TaskGraphBuilder — build task DAG
7. WorkflowGenerator — generate executable workflow YAML
8. ProviderAssignment — assign providers/agents/transports
9. ExecutionPlanner — plan execution batches
10. VerificationManager — verify task/phase/project completion
11. ArtifactValidator — validate artifacts
12. CompletionChecker — check completion status
13. DeploymentPlanner — generate deployment plan
14. DocumentationGenerator — generate documentation
15. StateManager — track project state
16. ResumeManager — resume after interruption
17. RollbackManager — manage checkpoints and rollback
18. ProgressTracker — track progress metrics
19. DependencyGraph — manage dependency graph

Owns the project lifecycle from idea to complete executable project.

Usage:
    >>> builder = ProjectBuilder(config=BuilderConfig())
    >>> result = builder.build("Build a Food Delivery Platform")
    >>> print(result["project_id"])
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.builder.data_models import (
    BuilderConfig,
    CheckpointRecord,
    CompletionStatus,
    ExecutionBatch,
    PhaseState,
    ProgressSnapshot,
    ProjectState,
    ResourceAssignment,
    TaskGraph,
    TaskStatus,
    VerificationResult,
)
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
from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


@dataclass
class ProjectBuilderConfig:
    """Configuration for the Project Builder.

    Attributes:
        builder: Builder configuration.
        auto_execute: Whether to automatically execute generated workflows.
        create_checkpoints: Whether to create checkpoints during execution.
        verify_after_tasks: Whether to verify after each task.
        generate_docs: Whether to generate documentation.
        generate_deployment: Whether to generate deployment plans.
    """

    builder: BuilderConfig = field(default_factory=BuilderConfig)
    auto_execute: bool = False
    create_checkpoints: bool = True
    verify_after_tasks: bool = True
    generate_docs: bool = True
    generate_deployment: bool = True


class ProjectBuilder:
    """Main orchestrator for autonomous project building.

    Transforms a simple natural-language idea into a complete executable
    project with architecture, workflows, tasks, documentation, and
    deployment plans.

    The lifecycle is:
    1. Initialize → 2. Classify → 3. Requirements → 4. Architecture →
    5. Roadmap → 6. Tasks → 7. Workflows → 8. Assign → 9. Plan →
    10. Execute → 11. Verify → 12. Document → 13. Deploy → Complete
    """

    # Minimum version of the builder package
    VERSION = "1.0.0"

    def __init__(
        self,
        config: ProjectBuilderConfig | None = None,
        event_bus: EventBus | None = None,
        kernel: Any = None,
    ) -> None:
        """Initialize the Project Builder.

        Args:
            config: Builder configuration. Uses defaults if not provided.
            event_bus: Optional EventBus for publishing events.
            kernel: Optional Kernel for service resolution.
        """
        self._config = config or ProjectBuilderConfig()
        self._kernel = kernel
        self._event_bus = event_bus or self._resolve_event_bus()

        # Initialize all subsystems
        self._initializer = ProjectInitializer(
            config=self._config.builder,
            event_bus=self._event_bus,
        )
        self._classifier = ProjectClassifier(event_bus=self._event_bus)
        self._extractor = RequirementExtractor(event_bus=self._event_bus)
        self._arch_gen = ArchitectureGenerator(event_bus=self._event_bus)
        self._roadmap_gen = RoadmapGenerator(event_bus=self._event_bus)
        self._task_graph_builder = TaskGraphBuilder(event_bus=self._event_bus)
        self._workflow_gen = WorkflowGenerator(event_bus=self._event_bus)
        self._provider_assignment = ProviderAssignment(
            decision_engine=self._resolve_decision_engine(),
            event_bus=self._event_bus,
        )
        self._execution_planner = ExecutionPlanner(event_bus=self._event_bus)
        self._artifact_validator = ArtifactValidator(event_bus=self._event_bus)
        self._verification_mgr = VerificationManager(
            artifact_validator=self._artifact_validator,
            event_bus=self._event_bus,
        )
        self._completion_checker = CompletionChecker(event_bus=self._event_bus)
        self._deployment_planner = DeploymentPlanner(event_bus=self._event_bus)
        self._docs_gen = DocumentationGenerator(event_bus=self._event_bus)
        self._state_mgr = StateManager(
            state_dir=self._config.builder.state_dir,
            event_bus=self._event_bus,
        )
        self._resume_mgr = ResumeManager(
            state_dir=self._config.builder.state_dir,
            event_bus=self._event_bus,
        )
        self._rollback_mgr = RollbackManager(
            state_dir=self._config.builder.state_dir,
            event_bus=self._event_bus,
        )
        self._progress_tracker = ProgressTracker(event_bus=self._event_bus)
        self._dependency_graph = DependencyGraph(event_bus=self._event_bus)

        # Execution state
        self._current_project_id: str = ""
        self._task_graph: TaskGraph | None = None
        self._project_state: ProjectState | None = None
        self._batches: list[ExecutionBatch] = []
        self._requirements: dict[str, Any] = {}
        self._architecture: dict[str, Any] = {}
        self._roadmap: dict[str, Any] = {}
        self._assignments: list[ResourceAssignment] = []
        self._deployment_plan: Any = None
        self._documentation: Any = None

    # ------------------------------------------------------------------
    # Service resolution
    # ------------------------------------------------------------------

    def _resolve_event_bus(self) -> EventBus | None:
        """Resolve EventBus from the kernel if available.

        Returns:
            EventBus instance or None.
        """
        if self._kernel is None:
            return None
        try:
            return self._kernel.get_service("event_bus")
        except Exception:
            return None

    def _resolve_decision_engine(self) -> Any:
        """Resolve Decision Engine from the kernel if available.

        Returns:
            Decision Engine instance or None.
        """
        if self._kernel is None:
            return None
        try:
            return self._kernel.get_service("decision_engine")
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Main build entry point
    # ------------------------------------------------------------------

    def build(self, idea: str, project_name: str = "") -> dict[str, Any]:
        """Build a complete project from a natural-language idea.

        This is the primary entry point. It orchestrates the entire
        project lifecycle.

        Args:
            idea: The natural-language project idea (e.g., "Build a Food Delivery Platform").
            project_name: Optional explicit project name.

        Returns:
            Dict with build results including project_id, status, and artifacts.
        """
        pid = uuid.uuid4().hex[:12]
        name = project_name or self._derive_project_name(idea)
        start_time = time.time()

        self._publish_event("builder.started", {
            "project_id": pid,
            "project_name": name,
            "idea": idea[:200],
        })

        logger.info("Building project '%s' from idea: %s", name, idea[:100])

        try:
            # Phase 1: Initialize
            self._project_state = self._initializer.initialize(name, idea)
            pid = self._project_state.project_id
            self._current_project_id = pid
            self._state_mgr.initialize(self._project_state)
            self._resume_mgr.set_crash_flag()

            contract = self._initializer.create_contract(
                pid, name, f"Build a {idea.strip().lower()}",
            )
            self._initializer.register_session(pid, name)

            # Phase 2: Classify
            self._state_mgr.transition_to("classifying")
            project_type = self._classifier.classify(idea, name)
            self._project_state.project_type = project_type.value

            # Phase 3: Requirements
            self._state_mgr.transition_to("requirements")
            self._requirements = self._extractor.extract(idea, name)

            # Phase 4: Architecture
            self._state_mgr.transition_to("architecture")
            self._architecture = self._arch_gen.generate(self._requirements, project_type)

            # Phase 5: Roadmap
            self._state_mgr.transition_to("planning")
            self._roadmap = self._roadmap_gen.generate(self._requirements, self._architecture)
            self._publish_event("builder.plan_created", {
                "project_id": pid,
                "phase_count": self._roadmap.get("total_phases", 0),
                "estimated_complexity": self._roadmap.get("estimated_complexity", "medium"),
            })

            # Phase 6: Task Graph
            self._state_mgr.transition_to("task_creation")
            self._task_graph = self._task_graph_builder.build(
                self._roadmap, self._requirements, self._architecture, pid,
            )
            self._dependency_graph.load(self._task_graph)

            # Check for cycles
            if self._dependency_graph.has_cycles():
                cycles = self._dependency_graph.find_cycles()
                logger.warning("Detected %d cycles in task graph", len(cycles))

            # Create phase checkpoint
            if self._config.create_checkpoints:
                self._rollback_mgr.create_checkpoint(
                    self._project_state, self._task_graph,
                    checkpoint_type="phase",
                )

            # Phase 7: Workflow Generation
            self._state_mgr.transition_to("workflow_generation")
            project_root = self._resolve_project_root(name)
            workflows_dir = str(project_root / self._config.builder.workflows_dir)
            workflow_paths = self._workflow_gen.generate(self._task_graph, workflows_dir)

            # Phase 8: Provider Assignment
            self._state_mgr.transition_to("provider_assignment")
            self._assignments = self._provider_assignment.assign(self._task_graph)

            # Phase 9: Execution Planning
            self._state_mgr.transition_to("execution_planning")
            self._batches = self._execution_planner.plan(
                self._task_graph, self._assignments,
                max_concurrent=self._config.builder.max_concurrent_tasks,
            )

            # Import and execute the generated workflows
            self._state_mgr.transition_to("executing")
            self._publish_event("builder.execution_started", {
                "project_id": pid,
                "batch_count": len(self._batches),
                "total_tasks": len(self._task_graph.nodes) if self._task_graph else 0,
            })
            self._execute_project(pid)

            # Phase 11: Verification
            self._state_mgr.transition_to("verifying")
            self._verify_project()

            # Phase 12: Documentation
            if self._config.generate_docs:
                self._state_mgr.transition_to("documenting")
                self._documentation = self._docs_gen.generate_all(
                    name, self._requirements, self._architecture,
                    self._roadmap, self._task_graph, self._project_state,
                )
                docs_dir = str(project_root / self._config.builder.docs_dir)
                self._docs_gen.write_all(self._documentation, docs_dir)

            # Phase 13: Deployment
            if self._config.generate_deployment:
                self._state_mgr.transition_to("deploying")
                self._deployment_plan = self._deployment_planner.plan(
                    self._architecture, pid, name,
                )

            # Complete
            duration = time.time() - start_time
            self._complete_project(success=True, duration=duration)

            result = self._build_result(pid, name, project_type, duration)

            self._resume_mgr.clear_crash_flag()

            logger.info(
                "Project '%s' built successfully in %.1fs (type: %s, %d tasks, %d workflows)",
                name, duration, project_type.value,
                len(self._task_graph.nodes) if self._task_graph else 0,
                len(workflow_paths),
            )

            return result

        except Exception as exc:
            duration = time.time() - start_time
            logger.error("Project build failed: %s", exc, exc_info=True)
            self._complete_project(success=False, duration=duration)

            return {
                "project_id": pid,
                "project_name": name,
                "status": "failed",
                "error": str(exc),
                "duration_seconds": round(duration, 2),
            }

    def _derive_project_name(self, idea: str) -> str:
        """Derive a project name from the idea.

        Args:
            idea: The natural-language project idea.

        Returns:
            A project name derived from the idea.
        """
        # Take first meaningful words
        words = idea.strip().split()
        # Remove leading "build", "create", "make", "develop"
        skip_words = {"build", "create", "make", "develop", "an", "a", "the"}
        meaningful = [w for w in words if w.lower() not in skip_words]
        if not meaningful:
            return "Project"
        return " ".join(meaningful[:5]).title()

    def _resolve_project_root(self, project_name: str) -> Path:
        """Resolve the project root directory.

        Args:
            project_name: The project name.

        Returns:
            Path to the project root.
        """
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in project_name)
        safe_name = safe_name.strip().replace(" ", "_").lower()

        project_root = Path(self._config.builder.project_root)
        if not project_root.is_absolute():
            project_root = Path.cwd() / project_root

        return project_root / safe_name

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _execute_project(self, project_id: str) -> None:
        """Execute the project's tasks in planned batches.

        Args:
            project_id: The project identifier.
        """
        if not self._task_graph or not self._batches:
            logger.info("No tasks to execute (planning only)")
            return

        if not self._config.auto_execute:
            logger.info("Auto-execution disabled, skipping task execution")
            return

        self._progress_tracker.start_timing()

        for batch in self._batches:
            logger.info(
                "Executing batch '%s' (%s, %d tasks)",
                batch.batch_id, batch.mode, len(batch.tasks),
            )

            batch_outputs: dict[str, dict[str, Any]] = {}

            for task_id in batch.tasks:
                node = self._task_graph.nodes.get(task_id)
                if node is None:
                    continue

                # Execute task (in a real implementation, this would dispatch
                # through the WorkflowEngine/ExecutionEngine)
                task_output = self._execute_task(node)
                batch_outputs[task_id] = task_output

                # Record progress
                if task_output.get("success", False):
                    self._progress_tracker.record_task_completion(
                        task_id,
                        provider_id=task_output.get("provider_id", ""),
                        agent_id=task_output.get("agent_id", ""),
                        duration_ms=task_output.get("duration_ms", 0),
                    )
                    node.status = TaskStatus.COMPLETED
                    self._state_mgr.record_completed_task(task_id, node.phase)
                else:
                    self._progress_tracker.record_task_failure(
                        task_id,
                        provider_id=task_output.get("provider_id", ""),
                        agent_id=task_output.get("agent_id", ""),
                    )
                    node.status = TaskStatus.FAILED
                    self._state_mgr.record_failed_task(task_id, node.phase)

            # Verify after batch if configured
            if self._config.verify_after_tasks:
                for task_id, task_output in batch_outputs.items():
                    self._verification_mgr.verify_task(task_id, task_output)

            # Create checkpoint if configured
            if self._config.create_checkpoints and batch.checkpoint_after:
                self._rollback_mgr.create_checkpoint(
                    self._project_state, self._task_graph,
                    checkpoint_type="automatic",
                )

    def _execute_task(self, node: TaskNode) -> dict[str, Any]:
        """Execute a single task.

        Args:
            node: The task node to execute.

        Returns:
            Dict with execution results.
        """
        # In a real implementation, this would use:
        # - WorkflowEngine to run the generated workflow
        # - ExecutionEngine to execute individual steps
        # - ProviderRuntime/AgentRuntime for AI task execution
        start = time.time()

        return {
            "success": True,
            "task_id": node.task_id,
            "duration_ms": (time.time() - start) * 1000,
            "output": f"Executed: {node.name}",
            "provider_id": "",
            "agent_id": "",
        }

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def _verify_project(self) -> VerificationResult | None:
        """Verify the complete project.

        Returns:
            VerificationResult for the project.
        """
        if not self._task_graph:
            return None

        result = self._verification_mgr.verify_project(
            self._current_project_id,
            {"task_graph": self._task_graph},
        )

        if result.passed:
            logger.info("Project verification passed")
        else:
            logger.warning("Project verification had %d issues", len(result.issues))

        return result

    # ------------------------------------------------------------------
    # Completion
    # ------------------------------------------------------------------

    def _complete_project(self, success: bool, duration: float) -> None:
        """Mark the project as complete.

        Args:
            success: Whether the project completed successfully.
            duration: Total build duration.
        """
        if self._project_state:
            self._state_mgr.update_status("completed" if success else "failed")
            self._state_mgr.transition_to("completed" if success else "failed")

            self._project_state.status = "completed" if success else "failed"
            self._project_state.completed_at = datetime.now(timezone.utc).isoformat()

        event_type = "builder.project_completed" if success else "builder.failed"
        self._publish_event(event_type, {
            "project_id": self._current_project_id,
            "duration_seconds": round(duration, 2),
            "success": success,
        })

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def _build_result(
        self,
        project_id: str,
        project_name: str,
        project_type: ProjectType,
        duration: float,
    ) -> dict[str, Any]:
        """Assemble the build result dictionary.

        Args:
            project_id: The project identifier.
            project_name: The project name.
            project_type: The project type.
            duration: Total build duration.

        Returns:
            Dict with complete build results.
        """
        snapshot = self._progress_tracker.get_snapshot(self._task_graph)
        project_root = self._resolve_project_root(project_name)

        return {
            "project_id": project_id,
            "project_name": project_name,
            "project_type": project_type.value,
            "status": "completed",
            "duration_seconds": round(duration, 2),
            "project_root": str(project_root),
            "task_count": len(self._task_graph.nodes) if self._task_graph else 0,
            "workflow_count": len(self._batches) if self._batches else 0,
            "assignment_count": len(self._assignments),
            "phases": list(self._project_state.phases.keys()) if self._project_state else [],
            "phases_completed": self._project_state.completed_phases if self._project_state else [],
            "progress": {
                "completed_tasks": snapshot.completed_tasks,
                "failed_tasks": snapshot.failed_tasks,
                "total_tasks": snapshot.total_tasks,
                "retries": snapshot.retries,
                "duration_seconds": snapshot.duration_seconds,
                "completion_percentage": round(
                    (snapshot.completed_tasks / max(snapshot.total_tasks, 1)) * 100, 1
                ),
            },
            "requirements": self._requirements,
            "architecture": self._architecture,
            "roadmap": self._roadmap,
            "deployment_plan": self._deployment_plan,
            "documentation": bool(self._documentation),
            "has_cycles": self._dependency_graph.has_cycles() if self._task_graph else False,
            "critical_path": self._dependency_graph.critical_path() if self._task_graph else [],
        }

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    def get_progress(self) -> ProgressSnapshot | None:
        """Get current progress snapshot.

        Returns:
            Current ProgressSnapshot or None.
        """
        return self._progress_tracker.get_snapshot(self._task_graph)

    def get_summary(self) -> dict[str, Any]:
        """Get a human-readable project summary.

        Returns:
            Dict with summary information.
        """
        return self._progress_tracker.get_summary(self._task_graph)

    def check_completion(self, scope: str = "project") -> CompletionStatus:
        """Check completion status.

        Args:
            scope: The scope to check (task, phase, project).

        Returns:
            CompletionStatus for the requested scope.
        """
        if not self._task_graph or not self._project_state:
            return CompletionStatus(
                scope=scope, target_id="",
                is_complete=False, can_proceed=False,
            )

        if scope == "project":
            return self._completion_checker.check_project(
                self._current_project_id, self._task_graph,
                self._project_state.completed_phases,
            )
        elif scope.startswith("phase_"):
            return self._completion_checker.check_phase(
                scope.replace("phase_", ""), self._task_graph,
            )

        return CompletionStatus(
            scope=scope, target_id=self._current_project_id,
            is_complete=False, can_proceed=True,
        )

    def impact_analysis(self, task_id: str) -> dict[str, Any]:
        """Analyze the impact of changing a task.

        Args:
            task_id: The task to analyze.

        Returns:
            Impact analysis dict.
        """
        return self._dependency_graph.impact_analysis(task_id)

    # ------------------------------------------------------------------
    # Checkpoint and rollback
    # ------------------------------------------------------------------

    def create_checkpoint(
        self,
        checkpoint_type: str = "manual",
        description: str = "",
    ) -> CheckpointRecord | None:
        """Create a manual checkpoint.

        Args:
            checkpoint_type: Type of checkpoint.
            description: Description of the checkpoint.

        Returns:
            The created CheckpointRecord, or None.
        """
        if not self._project_state or not self._task_graph:
            return None
        return self._rollback_mgr.create_checkpoint(
            self._project_state, self._task_graph,
            checkpoint_type=checkpoint_type,
            description=description,
        )

    def rollback(self, checkpoint_id: str) -> Any:
        """Rollback to a specific checkpoint.

        Args:
            checkpoint_id: The checkpoint to restore.

        Returns:
            RollbackResult.
        """
        return self._rollback_mgr.rollback_to(checkpoint_id)

    def list_checkpoints(self) -> list[CheckpointRecord]:
        """List all available checkpoints.

        Returns:
            List of CheckpointRecord objects.
        """
        return self._rollback_mgr.list_checkpoints()

    # ------------------------------------------------------------------
    # Resume
    # ------------------------------------------------------------------

    def detect_resume(self) -> dict[str, Any]:
        """Detect if a project can be resumed.

        Returns:
            Resume context dict.
        """
        return self._resume_mgr.detect_resume_context()

    def resume(self) -> dict[str, Any] | None:
        """Resume a previously interrupted project build.

        Returns:
            Build result dict or None.
        """
        context = self._resume_mgr.detect_resume_context()
        if not context.get("can_resume"):
            logger.info("No project to resume")
            return None

        project_state = self._resume_mgr.resume(context)
        if project_state is None:
            return None

        self._project_state = project_state
        self._current_project_id = project_state.project_id
        self._state_mgr.initialize(project_state)

        logger.info("Resumed project '%s' at phase '%s'", project_state.project_name, project_state.current_phase)
        return {
            "project_id": project_state.project_id,
            "project_name": project_state.project_name,
            "status": "resumed",
            "current_phase": project_state.current_phase,
        }

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish a builder event.

        Args:
            event_type: The event type string.
            data: Event payload.
        """
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(
                type=event_type, data=data, source="project_builder",
            ))
        except Exception:
            logger.debug("Failed to publish event '%s'", event_type, exc_info=True)
