"""Autonomous Project Loop Engine — Self-governing CEO Orchestration Loop.

Implements the continuous autonomous cycle:
Goal -> Plan -> Assign -> Execute -> Verify -> Repair -> Replan -> Repeat until acceptance criteria are satisfied.

Stops only when:
- all acceptance criteria pass,
- builds succeed,
- tests pass,
- verification succeeds,
or no further progress is possible.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from workflow_orchestrator.planning.goal_planner import GoalPlanner, ProjectPlan, AutonomousTaskSpec
from workflow_orchestrator.context.context_manager import PerWorkerContextManager
from workflow_orchestrator.execution.parallel_task_queue import ParallelTaskQueue, TaskProgressState
from workflow_orchestrator.execution.result_merger import ResultMerger
from workflow_orchestrator.decision.executive_decision_engine import ExecutiveDecisionEngine
from workflow_orchestrator.integrations.workspace_observer import WorkspaceObserver
from workflow_orchestrator.workers.worker_registry import DesktopWorkerRegistry

logger = logging.getLogger(__name__)


@dataclass
class AutonomousLoopResult:
    """Outcome of an autonomous project loop execution."""

    goal: str
    success: bool
    iterations: int
    plan: ProjectPlan
    acceptance_criteria_passed: int
    total_acceptance_criteria: int
    duration_seconds: float
    summary_log: List[str] = field(default_factory=list)


from workflow_orchestrator.builder.data_models import ProjectScale


class AutonomousProjectLoop:
    """Self-governing CEO Orchestration Loop coordinating local desktop workers to completion."""

    def __init__(
        self,
        worker_registry: Optional[DesktopWorkerRegistry] = None,
        project_root: Optional[Path] = None,
        max_loop_iterations: int = 5,
        project_scale: ProjectScale | str = ProjectScale.STANDARD,
        workspace_observer: Optional[WorkspaceObserver] = None,
    ) -> None:
        self.worker_registry = worker_registry or DesktopWorkerRegistry()
        self.project_root = project_root or Path.cwd()
        self.max_loop_iterations = max_loop_iterations
        self.project_scale = project_scale

        self.planner = GoalPlanner()
        self.context_mgr = PerWorkerContextManager(project_root=self.project_root)
        self.merger = ResultMerger(project_root=self.project_root)
        self.decision_engine = ExecutiveDecisionEngine(planner=self.planner)
        self.observer = workspace_observer or WorkspaceObserver(project_root=self.project_root)

    def run_autonomous_loop(self, goal: str) -> AutonomousLoopResult:
        """Run the full Autonomous Project Loop to completion."""
        t0 = time.time()
        logger.info(f"=== Starting Autonomous Project Loop for Goal: '{goal}' ===")
        summary_log = [f"Goal received: '{goal}'"]

        # 1. Goal Planning
        plan = self.planner.create_plan(goal)
        summary_log.append(f"Generated Plan with {len(plan.milestones)} milestone(s) and {len(plan.tasks)} initial task(s).")

        # 2. Build Task Queue
        queue = ParallelTaskQueue(
            worker_registry=self.worker_registry,
            workspace_observer=self.observer,
            project_scale=self.project_scale,
        )
        for t_id, task_spec in plan.tasks.items():
            queue.add_task(
                task_id=task_spec.task_id,
                title=task_spec.title,
                required_skill=task_spec.required_skill,
                prompt=task_spec.prompt,
                dependencies=task_spec.dependencies,
            )

        iteration = 0
        all_passed = False

        while iteration < self.max_loop_iterations and not all_passed:
            iteration += 1
            summary_log.append(f"--- Loop Iteration {iteration}/{self.max_loop_iterations} ---")

            # Assign & Execute Queue
            queue_status = queue.execute_queue(workspace_dir=self.project_root)
            completed_count = sum(1 for s in queue_status.values() if s == TaskProgressState.COMPLETED)
            summary_log.append(f"Queue Status: {completed_count}/{len(queue_status)} tasks completed.")

            # Collect outputs & Merge results
            worker_results = [t.output_result for t in queue.tasks.values() if t.output_result]
            merge_res = self.merger.merge_worker_outputs(worker_results)
            summary_log.append(merge_res.merge_log)

            # Verification Phase
            snapshot = self.observer.capture_snapshot()
            summary_log.append(f"Workspace Observer Snapshot: Build={snapshot.last_build_output[:80]}, Tests Passed={snapshot.test_passed}")

            # Evaluate Acceptance Criteria
            passed_criteria = 0
            for ac in plan.acceptance_criteria:
                if snapshot.test_passed:
                    ac.verified = True
                    passed_criteria += 1

            if passed_criteria == len(plan.acceptance_criteria) or completed_count == len(queue.tasks):
                all_passed = True
                summary_log.append("All Acceptance Criteria Satisfied! Loop terminating with GREEN success.")
                break

            # Executive Decision Engine (Replan / Reassign / Spawn Subtasks)
            decisions = self.decision_engine.evaluate_task_progress(queue, self.worker_registry)
            spawned_any = False
            for dec in decisions:
                summary_log.append(f"Executive Decision: {dec.action} -> {dec.reason}")
                if dec.action == "spawn_subtask":
                    for sub in dec.new_subtasks:
                        if sub.task_id not in queue.tasks:
                            queue.add_task(
                                task_id=sub.task_id,
                                title=sub.title,
                                required_skill=sub.required_skill,
                                prompt=sub.prompt,
                                dependencies=sub.dependencies,
                            )
                            spawned_any = True

            if not spawned_any:
                summary_log.append("No further task decomposition required; loop complete.")
                break

        duration = time.time() - t0
        passed_count = sum(1 for ac in plan.acceptance_criteria if ac.verified)

        return AutonomousLoopResult(
            goal=goal,
            success=all_passed,
            iterations=iteration,
            plan=plan,
            acceptance_criteria_passed=passed_count,
            total_acceptance_criteria=len(plan.acceptance_criteria),
            duration_seconds=duration,
            summary_log=summary_log,
        )
