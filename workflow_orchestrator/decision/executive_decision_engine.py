"""Executive Decision Engine — dynamic progress monitoring, stall detection, replanning, and subtask spawning.

Continuously monitors progress, detects blocked tasks, replans automatically, reassigns workers, and spawns subtasks.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from workflow_orchestrator.planning.goal_planner import ProjectPlan, AutonomousTaskSpec, GoalPlanner
from workflow_orchestrator.execution.parallel_task_queue import ParallelTaskQueue, TaskProgressState
from workflow_orchestrator.workers.worker_registry import DesktopWorkerRegistry

logger = logging.getLogger(__name__)


@dataclass
class ExecutiveDecision:
    action: str  # "continue", "reassign", "spawn_subtask", "replan", "terminate"
    target_task_id: Optional[str] = None
    reason: str = ""
    new_subtasks: List[AutonomousTaskSpec] = field(default_factory=list)


class ExecutiveDecisionEngine:
    """CEO Executive Decision Engine for continuous supervision, stall detection, and dynamic replanning."""

    def __init__(self, planner: Optional[GoalPlanner] = None) -> None:
        self.planner = planner or GoalPlanner()

    def evaluate_task_progress(
        self,
        task_queue: ParallelTaskQueue,
        worker_registry: DesktopWorkerRegistry,
    ) -> List[ExecutiveDecision]:
        """Evaluate task queue execution state and make executive decisions."""
        decisions = []

        for task_id, task in task_queue.tasks.items():
            # 1. Detect Blocked or Failed Tasks
            if task.state == TaskProgressState.FAILED:
                if task.retry_count < task.max_retries:
                    decisions.append(ExecutiveDecision(
                        action="reassign",
                        target_task_id=task_id,
                        reason=f"Task '{task_id}' failed attempt {task.retry_count}; reassigning to alternate worker.",
                    ))
                else:
                    # Spawn subtasks for decomposition
                    subtask_specs = self.planner.decompose_task(
                        AutonomousTaskSpec(
                            task_id=task.task_id,
                            milestone_id="m_repair",
                            title=task.title,
                            required_skill=task.required_skill,
                            prompt=task.prompt,
                            dependencies=task.dependencies,
                        ),
                        reason=f"Max retries reached: {task.error_log or 'Unknown error'}",
                    )
                    decisions.append(ExecutiveDecision(
                        action="spawn_subtask",
                        target_task_id=task_id,
                        reason=f"Decomposing blocked task '{task_id}' into subtasks.",
                        new_subtasks=subtask_specs,
                    ))

        return decisions
