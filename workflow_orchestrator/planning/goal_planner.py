"""Goal Planner & Dynamic Task Decomposition Engine.

Converts a natural-language goal into milestones, tasks, dependencies, risks, and acceptance criteria.
Breaks large tasks into smaller executable subtasks dynamically.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AcceptanceCriterion:
    criterion_id: str
    description: str
    verified: bool = False
    verification_type: str = "pytest"  # pytest, build, lint, file_exist


@dataclass
class Milestone:
    milestone_id: str
    title: str
    description: str
    tasks: List[str] = field(default_factory=list)
    completed: bool = False


@dataclass
class AutonomousTaskSpec:
    task_id: str
    milestone_id: str
    title: str
    required_skill: str  # backend_api, frontend_ui, unit_testing, deployment, refactoring
    prompt: str
    dependencies: List[str] = field(default_factory=list)
    acceptance_criteria: List[AcceptanceCriterion] = field(default_factory=list)
    subtasks: List[str] = field(default_factory=list)
    is_subtask: bool = False
    parent_task_id: Optional[str] = None


@dataclass
class ProjectPlan:
    goal: str
    milestones: List[Milestone] = field(default_factory=list)
    tasks: Dict[str, AutonomousTaskSpec] = field(default_factory=dict)
    risks: List[str] = field(default_factory=list)
    acceptance_criteria: List[AcceptanceCriterion] = field(default_factory=list)


class GoalPlanner:
    """Parses natural-language goals and decomposes them into executable task graphs with acceptance criteria."""

    def create_plan(self, goal: str) -> ProjectPlan:
        """Parse natural-language goal and generate complete milestone and task graph."""
        logger.info(f"GoalPlanner creating plan for: '{goal}'")

        # 1. Acceptance Criteria Extraction
        criteria = [
            AcceptanceCriterion("ac_01", "Backend API routes compiled and functional", verification_type="build"),
            AcceptanceCriterion("ac_02", "Frontend UI components rendered cleanly", verification_type="file_exist"),
            AcceptanceCriterion("ac_03", "Unit test suite executes with zero failures", verification_type="pytest"),
            AcceptanceCriterion("ac_04", "Production container configuration generated", verification_type="file_exist"),
        ]

        # 2. Risk Identification
        risks = [
            "API endpoint schema mismatch with frontend types",
            "Missing local desktop tool CLI binary dependencies",
            "Unit test execution failure due to invalid imports",
        ]

        # 3. Milestone & Task Decomposition
        m1 = Milestone("m_01", "Foundation & Architecture", ["t_arch", "t_schema"])
        m2 = Milestone("m_02", "Backend & Frontend Implementation", ["t_backend", "t_frontend"])
        m3 = Milestone("m_03", "Testing, Repair & Deployment", ["t_tests", "t_deploy"])

        tasks = {}

        # Architecture & Schema
        t_arch = AutonomousTaskSpec(
            task_id="t_arch",
            milestone_id="m_01",
            title="Setup Project Architecture",
            required_skill="architecture",
            prompt=f"Set up directory structure and package configs for: {goal}",
            acceptance_criteria=[criteria[0]],
        )
        tasks[t_arch.task_id] = t_arch

        t_schema = AutonomousTaskSpec(
            task_id="t_schema",
            milestone_id="m_01",
            title="Define Data Models & Schemas",
            required_skill="backend_api",
            prompt=f"Create Pydantic and database schemas for: {goal}",
            dependencies=["t_arch"],
        )
        tasks[t_schema.task_id] = t_schema

        # Core Implementation
        t_backend = AutonomousTaskSpec(
            task_id="t_backend",
            milestone_id="m_02",
            title="Implement Backend API Routes",
            required_skill="backend_api",
            prompt=f"Implement REST API endpoints for: {goal}",
            dependencies=["t_schema"],
            acceptance_criteria=[criteria[0]],
        )
        tasks[t_backend.task_id] = t_backend

        t_frontend = AutonomousTaskSpec(
            task_id="t_frontend",
            milestone_id="m_02",
            title="Implement Frontend UI Components",
            required_skill="frontend_ui",
            prompt=f"Implement React/Next.js UI components for: {goal}",
            dependencies=["t_backend"],
            acceptance_criteria=[criteria[1]],
        )
        tasks[t_frontend.task_id] = t_frontend

        # Quality & Deployment
        t_tests = AutonomousTaskSpec(
            task_id="t_tests",
            milestone_id="m_03",
            title="Create & Run Unit Test Suite",
            required_skill="unit_testing",
            prompt=f"Write and verify Pytest test suite for: {goal}",
            dependencies=["t_backend"],
            acceptance_criteria=[criteria[2]],
        )
        tasks[t_tests.task_id] = t_tests

        t_deploy = AutonomousTaskSpec(
            task_id="t_deploy",
            milestone_id="m_03",
            title="Generate Deployment Configuration",
            required_skill="deployment",
            prompt=f"Generate Docker and deployment manifests for: {goal}",
            dependencies=["t_frontend", "t_tests"],
            acceptance_criteria=[criteria[3]],
        )
        tasks[t_deploy.task_id] = t_deploy

        return ProjectPlan(
            goal=goal,
            milestones=[m1, m2, m3],
            tasks=tasks,
            risks=risks,
            acceptance_criteria=criteria,
        )

    def decompose_task(self, task: AutonomousTaskSpec, reason: str) -> List[AutonomousTaskSpec]:
        """Dynamically decompose a complex or failed task into smaller subtasks."""
        logger.info(f"Decomposing task '{task.task_id}' into subtasks due to: {reason}")
        subtask1 = AutonomousTaskSpec(
            task_id=f"{task.task_id}_sub_1",
            milestone_id=task.milestone_id,
            title=f"{task.title} - Core Logic",
            required_skill=task.required_skill,
            prompt=f"{task.prompt} (Focus: Core implementation logic)",
            dependencies=task.dependencies,
            is_subtask=True,
            parent_task_id=task.task_id,
        )
        subtask2 = AutonomousTaskSpec(
            task_id=f"{task.task_id}_sub_2",
            milestone_id=task.milestone_id,
            title=f"{task.title} - Verification & Fixes",
            required_skill=task.required_skill,
            prompt=f"{task.prompt} (Focus: Error fixes and verification)",
            dependencies=[subtask1.task_id],
            is_subtask=True,
            parent_task_id=task.task_id,
        )
        task.subtasks = [subtask1.task_id, subtask2.task_id]
        return [subtask1, subtask2]
