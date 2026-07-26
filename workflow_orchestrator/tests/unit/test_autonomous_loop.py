"""Unit tests for Autonomous Project Loop, Goal Planner, Context Manager, Result Merger, and Executive Decision Engine.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from workflow_orchestrator.planning.goal_planner import GoalPlanner, ProjectPlan, AutonomousTaskSpec
from workflow_orchestrator.context.context_manager import PerWorkerContextManager
from workflow_orchestrator.execution.result_merger import ResultMerger
from workflow_orchestrator.decision.executive_decision_engine import ExecutiveDecisionEngine
from workflow_orchestrator.orchestrator.autonomous_loop import AutonomousProjectLoop, AutonomousLoopResult
from workflow_orchestrator.workers.desktop_worker import DesktopWorkerTaskResult
from workflow_orchestrator.workers.worker_registry import DesktopWorkerRegistry
from workflow_orchestrator.workers.implementations import CursorDesktopWorker, CopilotDesktopWorker
from workflow_orchestrator.orchestrator.orchestrator import Orchestrator


class TestAutonomousLoopEngine:
    def test_goal_planner_creation_and_decomposition(self):
        planner = GoalPlanner()
        plan = planner.create_plan("Build a Todo App with FastAPI and Next.js")

        assert plan.goal == "Build a Todo App with FastAPI and Next.js"
        assert len(plan.milestones) == 3
        assert len(plan.tasks) >= 6
        assert len(plan.acceptance_criteria) >= 4
        assert len(plan.risks) >= 3

        # Test Dynamic Task Decomposition
        subtasks = planner.decompose_task(plan.tasks["t_backend"], reason="Complex module failure")
        assert len(subtasks) == 2
        assert subtasks[0].is_subtask is True
        assert subtasks[0].parent_task_id == "t_backend"

    def test_per_worker_context_manager(self):
        ctx_mgr = PerWorkerContextManager(project_root=Path.cwd())
        payload = ctx_mgr.build_scoped_payload(
            worker_id="cursor_desktop",
            task_id="t_frontend",
            raw_prompt="Build Next.js Frontend Dashboard",
            required_skill="frontend_ui",
        )

        assert payload["worker_id"] == "cursor_desktop"
        assert payload["task_id"] == "t_frontend"
        assert "[SCOPED WORKER CONTEXT]" in payload["prompt"]
        assert len(payload["scoped_files"]) >= 0

    def test_result_merger_and_conflict_resolution(self):
        merger = ResultMerger(project_root=Path.cwd())
        r1 = DesktopWorkerTaskResult(success=True, generated_files=[Path("pyproject.toml")])
        r2 = DesktopWorkerTaskResult(success=True, generated_files=[Path("pyproject.toml"), Path("README.md")])

        res = merger.merge_worker_outputs([r1, r2])
        assert res.success is True
        assert res.conflicts_resolved == 1
        assert len(res.unified_files) == 2

    def test_executive_decision_engine(self):
        planner = GoalPlanner()
        decision_engine = ExecutiveDecisionEngine(planner=planner)
        registry = DesktopWorkerRegistry()
        registry.register_worker(CursorDesktopWorker())

        # Verify evaluation
        from workflow_orchestrator.execution.parallel_task_queue import ParallelTaskQueue, TaskProgressState
        queue = ParallelTaskQueue(worker_registry=registry)
        t = queue.add_task("t_fail", "Failed Task", "backend_api", "Do something")
        t.state = TaskProgressState.FAILED
        t.retry_count = 3
        t.max_retries = 3

        decisions = decision_engine.evaluate_task_progress(queue, registry)
        assert len(decisions) >= 1
        assert decisions[0].action == "spawn_subtask"

    def test_autonomous_project_loop_execution(self):
        orch = Orchestrator.get_instance()
        loop = AutonomousProjectLoop(worker_registry=orch.worker_registry, project_root=Path.cwd(), max_loop_iterations=2)

        res = loop.run_autonomous_loop("Build a Todo App with FastAPI and Next.js")
        assert isinstance(res, AutonomousLoopResult)
        assert res.goal == "Build a Todo App with FastAPI and Next.js"
        assert res.iterations >= 1
        assert len(res.summary_log) > 0
        assert res.acceptance_criteria_passed >= 0
