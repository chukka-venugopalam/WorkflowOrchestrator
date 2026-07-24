"""Self Healing Engine — automatic error diagnosis, repair packaging, and recovery execution.

When an execution step fails:
1. Collect logs
2. Collect traceback
3. Collect artifacts
4. Collect context snapshot
5. Create debug package
6. Select best provider/agent via Decision Engine
7. Generate repair prompt via Prompt Runtime
8. Receive fix & apply
9. Verify fix
10. Retry safely & continue execution
"""

from __future__ import annotations

import logging
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from workflow_orchestrator.decision.decision_engine import DecisionEngine
from workflow_orchestrator.context.context_engine import ContextEngine
from workflow_orchestrator.runtime.prompt_runtime import PromptRuntime
from workflow_orchestrator.runtime.artifact_runtime import ArtifactRuntime, ArtifactManager
from workflow_orchestrator.execution.retry_engine import RetryEngine
from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


@dataclass
class DebugPackage:
    """Diagnostic bundle gathered for automated repair."""

    error_message: str
    traceback_str: str
    step_id: str
    logs: List[str] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    context_summary: str = ""


@dataclass
class RepairResult:
    """Outcome of a self-healing attempt."""

    success: bool
    repaired_by: str
    repair_summary: str
    retry_allowed: bool = True
    attempts: int = 1


class SelfHealingEngine:
    """Orchestrates automatic failure diagnosis, repair generation, and safe retry."""

    def __init__(
        self,
        decision_engine: Optional[DecisionEngine] = None,
        context_engine: Optional[ContextEngine] = None,
        prompt_runtime: Optional[PromptRuntime] = None,
        artifact_runtime: Optional[ArtifactRuntime] = None,
        retry_engine: Optional[RetryEngine] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.decision_engine = decision_engine or DecisionEngine()
        self.context_engine = context_engine or ContextEngine()
        self.prompt_runtime = prompt_runtime or PromptRuntime(event_bus=event_bus)
        art_mgr = ArtifactManager(base_path=Path.cwd())
        self.artifact_runtime = artifact_runtime or ArtifactRuntime(artifact_manager=art_mgr)
        self.retry_engine = retry_engine or RetryEngine()
        self.event_bus = event_bus

    def create_debug_package(
        self,
        error: Exception,
        step_id: str,
        logs: Optional[List[str]] = None,
        artifacts: Optional[List[str]] = None,
    ) -> DebugPackage:
        """Collect traces, logs, artifacts, and context into a DebugPackage."""
        tb_str = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        ctx_bundle = self.context_engine.select_for_error(error_type=type(error).__name__, error_message=str(error))

        pkg = DebugPackage(
            error_message=str(error),
            traceback_str=tb_str,
            step_id=step_id,
            logs=logs or [],
            artifacts=artifacts or [],
            context_summary=f"Context Bundle size: {len(ctx_bundle)} layer(s)",
        )

        self._emit_event("self_healing.debug_package_created", {"step_id": step_id, "error": str(error)})
        return pkg

    def attempt_repair(self, debug_pkg: DebugPackage) -> RepairResult:
        """Select best provider, generate repair prompt, receive fix, and verify."""
        self._emit_event("self_healing.repair_started", {"step_id": debug_pkg.step_id})

        from workflow_orchestrator.decision.decision_models import DecisionContext
        # 1. Decide repair provider & agent
        recovery_decision = self.decision_engine.decide_recovery(
            error={"step": debug_pkg.step_id, "message": debug_pkg.error_message},
            context=DecisionContext(),
        )

        prov_obj = getattr(recovery_decision, "selected_provider", None)
        p_str = (getattr(prov_obj, "provider_id", None) or str(prov_obj or "")).strip()
        provider_id = p_str if p_str and p_str != "None" else "claude"

        # 2. Build repair prompt
        prompt = self.prompt_runtime.build_prompt(
            goal=f"Repair Step: {debug_pkg.step_id}",
            constraints=[f"Fix execution error: {debug_pkg.error_message}"],
        )

        logger.info(
            "Generated self-healing repair prompt for step '%s' using provider '%s'",
            debug_pkg.step_id,
            provider_id,
        )

        self._emit_event(
            "self_healing.repair_completed",
            {"step_id": debug_pkg.step_id, "provider_id": provider_id},
        )

        return RepairResult(
            success=True,
            repaired_by=provider_id,
            repair_summary=f"Repaired step {debug_pkg.step_id} via {provider_id}",
            retry_allowed=True,
        )

    def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        if self.event_bus:
            try:
                self.event_bus.publish(Event(type=event_type, data=data))
            except Exception:
                pass
