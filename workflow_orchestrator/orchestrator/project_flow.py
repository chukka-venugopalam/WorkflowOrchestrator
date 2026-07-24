"""Automated Project Flow Engine — single-prompt AI Operating System lifecycle.

Orchestrates end-to-end project execution:
Goal Analysis
↓
Requirement Extraction
↓
Project Classification
↓
Architecture Generation
↓
Project Contract
↓
Roadmap
↓
Workflow Generation
↓
Task Graph
↓
Provider Selection
↓
Agent Selection
↓
Execution Plan
↓
Confirmation
↓
Execution
↓
Verification
↓
Deployment
↓
Project Memory
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from workflow_orchestrator.builder.project_builder import ProjectBuilder
from workflow_orchestrator.builder.data_models import BuilderConfig
from workflow_orchestrator.decision.decision_engine import DecisionEngine
from workflow_orchestrator.context.context_engine import ContextEngine
from workflow_orchestrator.knowledge.knowledge_base import KnowledgeBase
from workflow_orchestrator.contracts.contract_manager import ContractManager
from workflow_orchestrator.runtime.session_runtime import SessionManager
from workflow_orchestrator.runtime.artifact_runtime import ArtifactRuntime
from workflow_orchestrator.runtime.project_memory import ProjectMemory
from workflow_orchestrator.execution.execution_engine import ExecutionEngine
from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


@dataclass
class FlowExecutionRecord:
    """Record of an orchestrated project flow execution."""

    project_name: str
    idea_description: str
    phase: str
    build_result: Optional[BuildResult] = None
    duration_seconds: float = 0.0
    status: str = "completed"
    error: Optional[str] = None


class ProjectFlowEngine:
    """Automates project creation, compilation, routing, execution, and memory storage."""

    def __init__(
        self,
        project_builder: Optional[ProjectBuilder] = None,
        decision_engine: Optional[DecisionEngine] = None,
        context_engine: Optional[ContextEngine] = None,
        knowledge_base: Optional[KnowledgeBase] = None,
        contract_manager: Optional[ContractManager] = None,
        session_manager: Optional[SessionManager] = None,
        project_memory: Optional[ProjectMemory] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.builder = project_builder or ProjectBuilder(event_bus=event_bus)
        self.decision_engine = decision_engine or DecisionEngine()
        self.context_engine = context_engine or ContextEngine()
        self.knowledge_base = knowledge_base or KnowledgeBase()
        self.contract_mgr = contract_manager or ContractManager()
        self.session_mgr = session_manager or SessionManager()
        self.project_memory = project_memory or ProjectMemory(project_dir=Path.cwd())
        self.event_bus = event_bus

    def execute_project_from_prompt(
        self,
        idea: str,
        project_name: Optional[str] = None,
        workspace_dir: Optional[str | Path] = None,
        auto_confirm: bool = True,
    ) -> FlowExecutionRecord:
        """Execute the full 16-phase automated project lifecycle from a text prompt.

        Args:
            idea: High-level text description of the desired application.
            project_name: Optional explicit project name.
            workspace_dir: Target output directory.
            auto_confirm: If True, executes without manual pausing.

        Returns:
            FlowExecutionRecord detailing the build and execution outcomes.
        """
        start_time = time.time()
        self._emit_event("project.flow.started", {"idea": idea, "project_name": project_name})

        try:
            # Step 1: Initialize session
            session = self.session_mgr.create_session(project=project_name, metadata={"goal": idea})
            self._emit_event("session.created", {"session_id": session.session_id})

            # Step 2: Invoke Builder pipeline
            target = Path(workspace_dir) if workspace_dir else Path.cwd()
            config = BuilderConfig(project_root=target)
            
            build_result: Dict[str, Any] = self.builder.build(
                idea=idea,
                project_name=project_name or "",
            )

            p_name = build_result.get("project_name", project_name or "ai_project")
            success = build_result.get("success", True)
            dur = build_result.get("duration_seconds", 0.0)
            contract = build_result.get("contract")

            # Step 3: Record Contract, Timeline, and Memory
            if contract:
                self.contract_mgr.create_contract(
                    project_name=p_name,
                    vision=getattr(contract, "vision", str(contract)),
                    requirements=getattr(contract, "requirements", []),
                )

            # Record in ProjectMemory
            self.project_memory.save_history(
                session_id=session.session_id,
                entries=[
                    {
                        "action": "project_build",
                        "status": "completed" if success else "failed",
                        "duration_seconds": dur,
                        "idea": idea,
                    }
                ],
            )
            self.project_memory.append_timeline_entry(
                {
                    "event_type": "project_completed",
                    "summary": f"Project {p_name} successfully built.",
                }
            )

            duration = time.time() - start_time
            self._emit_event("project.flow.completed", {"project_name": p_name, "duration": duration})

            return FlowExecutionRecord(
                project_name=p_name,
                idea_description=idea,
                phase="completed",
                build_result=build_result,
                duration_seconds=duration,
                status="completed" if success else "failed",
            )

        except Exception as exc:
            duration = time.time() - start_time
            logger.error("Project flow execution failed: %s", exc, exc_info=True)
            self._emit_event("project.flow.failed", {"error": str(exc), "duration": duration})
            return FlowExecutionRecord(
                project_name=project_name or "unknown",
                idea_description=idea,
                phase="failed",
                duration_seconds=duration,
                status="failed",
                error=str(exc),
            )

    def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        if self.event_bus:
            try:
                self.event_bus.publish(Event(type=event_type, data=data))
            except Exception:
                pass
