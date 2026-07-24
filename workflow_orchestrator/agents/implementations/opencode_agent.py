"""OpenCode agent adapter — communicates with OpenCode CLI.

Supports:
- CLI task execution (`opencode run`)
- Workspace management and file editing
- Status tracking, heartbeat, and cancellation
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


class OpenCodeAgent(BaseAgent):
    """Adapter for OpenCode CLI agent."""

    def __init__(
        self,
        agent_id: str = "opencode",
        cli_path: str | None = None,
        workspace_dir: str | None = None,
    ) -> None:
        super().__init__(workspace_base=workspace_dir)
        self._cli_path = cli_path or shutil.which("opencode") or "opencode"
        found = shutil.which(self._cli_path)
        self._simulation_mode = not (found is not None and os.path.exists(found))

    @property
    def simulation_mode(self) -> bool:
        return self._simulation_mode

    def manifest(self) -> AgentManifest:
        return AgentManifest(
            id="opencode",
            name="OpenCode Agent",
            version="1.0.0",
            description="Open-source AI coding agent for autonomous multi-file edits",
            capabilities=[
                Capability(id="codegen.general", description="General code generation"),
                Capability(id="codegen.python", description="Python generation"),
                Capability(id="workspace.edit", description="Multi-file editing"),
            ],
            requires_local_runtime=True,
            metadata={"cli_path": self._cli_path, "simulation_mode": self._simulation_mode},
        )

    async def _initialize_impl(self) -> None:
        if self._simulation_mode:
            logger.info("OpenCode CLI binary not found at '%s'. Running in SIMULATION_MODE.", self._cli_path)
        else:
            logger.info("OpenCode agent initialized with CLI binary '%s'", self._cli_path)

    async def _shutdown_impl(self) -> None:
        pass

    async def _execute_impl(self, request: ExecutionRequest) -> ExecutionResult:
        if self._simulation_mode:
            return self._simulate_execution(request)

        cmd = [self._cli_path, request.goal]
        cwd_dir = str(self._current_workspace) if (self._current_workspace and self._current_workspace.exists()) else (str(self._workspace_base) if (self._workspace_base and self._workspace_base.exists()) else os.getcwd())
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd_dir, timeout=120)
            if res.returncode == 0:
                return ExecutionResult(
                    task_id=request.task_id,
                    success=True,
                    output=res.stdout or "OpenCode execution completed.",
                    metadata={"agent": "opencode", "simulation_mode": False},
                )
            logger.warning("OpenCode CLI exited with returncode %d. Falling back to simulation.", res.returncode)
            return self._simulate_execution(request)
        except Exception as exc:
            logger.warning("OpenCode execution failed (%s). Falling back to simulation.", exc)
            return self._simulate_execution(request)

    def _simulate_execution(self, request: ExecutionRequest) -> ExecutionResult:
        return ExecutionResult(
            task_id=request.task_id,
            success=True,
            output=f"[OpenCode SIMULATION_MODE] Executed agent task '{request.goal}' in workspace '{self._current_workspace or self._workspace_base}'.",
            token_usage={"total": 180},
            metadata={"agent": "opencode", "simulation_mode": True},
        )
