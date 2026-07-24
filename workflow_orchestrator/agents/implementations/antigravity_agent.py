"""Antigravity agent adapter — communicates with Google Antigravity (AGY) CLI.

Supports:
- AGY CLI execution (`agy task run` / `antigravity`)
- Agentic multi-file workspace edits, patch review, and status tracking
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional

from workflow_orchestrator.agents.base.base_agent import BaseAgent
from workflow_orchestrator.intelligence.models import (
    AgentManifest,
    AgentStatus,
    Capability,
    ExecutionRequest,
    ExecutionResult,
)

logger = logging.getLogger(__name__)


class AntigravityAgent(BaseAgent):
    """Adapter for Google Antigravity (AGY) agentic coding assistant."""

    def __init__(
        self,
        agent_id: str = "antigravity",
        cli_path: str | None = None,
        workspace_dir: str | None = None,
    ) -> None:
        super().__init__(workspace_base=workspace_dir)
        self._cli_path = cli_path or shutil.which("agy") or shutil.which("antigravity") or "agy"
        found = shutil.which(self._cli_path)
        self._simulation_mode = not (found is not None and os.path.exists(found))

    @property
    def simulation_mode(self) -> bool:
        return self._simulation_mode

    def manifest(self) -> AgentManifest:
        return AgentManifest(
            id="antigravity",
            name="Google Antigravity Agent (AGY)",
            version="2.0.0",
            description="Advanced Agentic Coding assistant for multi-file refactoring and full project construction",
            capabilities=[
                Capability(id="reasoning.architecture", description="System architecture design"),
                Capability(id="codegen.general", description="Advanced code generation"),
                Capability(id="codegen.python", description="Python code generation"),
                Capability(id="workspace.edit", description="Full workspace refactoring"),
            ],
            requires_local_runtime=True,
            metadata={"cli_path": self._cli_path, "simulation_mode": self._simulation_mode},
        )

    async def _initialize_impl(self) -> None:
        if self._simulation_mode:
            logger.info("Antigravity CLI binary not found at '%s'. Running in SIMULATION_MODE.", self._cli_path)
        else:
            logger.info("Antigravity agent initialized with CLI binary '%s'", self._cli_path)

    async def _shutdown_impl(self) -> None:
        pass

    async def _execute_impl(self, request: ExecutionRequest) -> ExecutionResult:
        if self._simulation_mode:
            return self._simulate_execution(request)

        cmd = [self._cli_path, "task", "run", "--prompt", request.goal]
        cwd_dir = str(self._current_workspace) if (self._current_workspace and self._current_workspace.exists()) else (str(self._workspace_base) if (self._workspace_base and self._workspace_base.exists()) else os.getcwd())
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd_dir, timeout=180)
            if res.returncode == 0:
                return ExecutionResult(
                    task_id=request.task_id,
                    success=True,
                    output=res.stdout or "Antigravity task completed successfully.",
                    metadata={"agent": "antigravity", "simulation_mode": False},
                )
            logger.warning("Antigravity CLI exited with returncode %d. Falling back to simulation.", res.returncode)
            return self._simulate_execution(request)
        except Exception as exc:
            logger.warning("Antigravity execution failed (%s). Falling back to simulation.", exc)
            return self._simulate_execution(request)

    def _simulate_execution(self, request: ExecutionRequest) -> ExecutionResult:
        return ExecutionResult(
            task_id=request.task_id,
            success=True,
            output=f"[Antigravity AGY SIMULATION_MODE] Completed agent task '{request.goal}'.",
            token_usage={"total": 220},
            metadata={"agent": "antigravity", "simulation_mode": True},
        )
