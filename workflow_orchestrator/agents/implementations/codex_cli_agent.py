"""Codex CLI agent adapter — wraps OpenAI's Codex CLI tool.

Communicates with Codex CLI for command-line code generation
and task execution through OpenAI's coding agent.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.agents.base import BaseAgent
from workflow_orchestrator.intelligence.models import (
    AgentManifest,
    Capability,
    ExecutionErrorType,
    ExecutionRequest,
    ExecutionResult,
)

logger = logging.getLogger(__name__)


class CodexCLIAgent(BaseAgent):
    """Agent adapter for OpenAI Codex CLI.

    Codex CLI is OpenAI's command-line coding agent. It generates
    and executes code based on natural language prompts.

    Requires the ``codex`` CLI to be installed.
    """

    def __init__(
        self,
        cli_path: str = "codex",
        workspace_base: Path | str | None = None,
    ) -> None:
        """Initialize the Codex CLI agent.

        Args:
            cli_path: Path to the Codex CLI executable.
            workspace_base: Base directory for agent workspaces.
        """
        super().__init__(workspace_base=workspace_base)
        self._cli_path = cli_path

    def manifest(self) -> AgentManifest:
        """Get the agent's declared manifest."""
        return AgentManifest(
            id="codex-cli",
            name="Codex CLI",
            version="1.0.0",
            description="OpenAI Codex CLI — command-line coding agent for code generation and execution",
            capabilities=[
                Capability(id="codegen.general", description="General code generation"),
                Capability(id="codegen.python", description="Python code generation"),
                Capability(id="codegen.typescript", description="TypeScript/JavaScript code generation"),
                Capability(id="codegen.web", description="Web development (HTML, CSS, JS)"),
                Capability(id="reasoning.analysis", description="Analysis and reasoning"),
            ],
            requires_local_runtime=True,
            supports_parallel_tasks=False,
            metadata={
                "cli_path": self._cli_path,
                "supports_code_execution": True,
            },
        )

    async def _launch_impl(self) -> None:
        """Verify that Codex CLI is available."""
        try:
            proc = await asyncio.create_subprocess_exec(
                self._cli_path, "--help",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate(timeout=10)
            if proc.returncode != 0:
                raise RuntimeError(f"Codex CLI check failed: {stderr.decode()}")
            logger.info("Codex CLI found")
        except FileNotFoundError:
            raise RuntimeError(
                f"Codex CLI not found at '{self._cli_path}'. "
                "Install it with 'pip install openai-codex' or 'npm install -g @openai/codex'"
            )

    async def _execute_impl(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute a task using Codex CLI.

        Args:
            request: The execution request.

        Returns:
            ExecutionResult with Codex CLI's output.
        """
        workspace = self.create_workspace(request.task_id)

        try:
            proc = await asyncio.create_subprocess_exec(
                self._cli_path, request.goal,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(workspace),
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=request.timeout_seconds or 120,
            )

            output = stdout.decode("utf-8", errors="replace")
            error_output = stderr.decode("utf-8", errors="replace")

            if proc.returncode != 0:
                return ExecutionResult(
                    task_id=request.task_id,
                    success=False,
                    output=output,
                    error_type=ExecutionErrorType.INTERNAL_ERROR,
                    error_message=error_output,
                )

            return ExecutionResult(
                task_id=request.task_id,
                success=True,
                output=output,
                metadata={"workspace": str(workspace)},
            )
        except asyncio.TimeoutError:
            return ExecutionResult(
                task_id=request.task_id,
                success=False,
                error_type=ExecutionErrorType.TIMEOUT,
                error_message=f"Codex CLI execution timed out after {request.timeout_seconds}s",
            )
        except Exception as exc:
            return ExecutionResult(
                task_id=request.task_id,
                success=False,
                error_type=ExecutionErrorType.INTERNAL_ERROR,
                error_message=str(exc),
            )
