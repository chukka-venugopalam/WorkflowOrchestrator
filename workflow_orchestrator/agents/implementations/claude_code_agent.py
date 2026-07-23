"""Claude Code agent adapter — wraps the Claude Code CLI tool.

Communicates with Claude Code via its CLI interface. Supports
code generation, analysis, and task execution through Claude's
terminal-based agent.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
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


class ClaudeCodeAgent(BaseAgent):
    """Agent adapter for Claude Code (terminal-based agent from Anthropic).

    Communicates with Claude Code via its CLI interface. Supports
    code generation, analysis, debugging, and file editing.

    Requires the ``claude`` CLI to be installed and authenticated.
    """

    def __init__(
        self,
        cli_path: str = "claude",
        workspace_base: Path | str | None = None,
    ) -> None:
        """Initialize the Claude Code agent.

        Args:
            cli_path: Path to the Claude CLI executable.
            workspace_base: Base directory for agent workspaces.
        """
        super().__init__(workspace_base=workspace_base)
        self._cli_path = cli_path
        self._process: asyncio.subprocess.Process | None = None

    def manifest(self) -> AgentManifest:
        """Get the agent's declared manifest."""
        return AgentManifest(
            id="claude-code",
            name="Claude Code",
            version="1.0.0",
            description="Anthropic's Claude Code — terminal-based AI coding agent for code generation and analysis",
            capabilities=[
                Capability(id="codegen.general", description="General code generation"),
                Capability(id="codegen.python", description="Python code generation"),
                Capability(id="codegen.typescript", description="TypeScript/JavaScript code generation"),
                Capability(id="codegen.web", description="Web development (HTML, CSS, JS)"),
                Capability(id="reasoning.code-review", description="Code review and quality analysis"),
                Capability(id="reasoning.architecture", description="Architecture design and evaluation"),
                Capability(id="reasoning.analysis", description="Deep analysis and reasoning"),
                Capability(id="verify.review", description="Code review and verification"),
            ],
            requires_local_runtime=True,
            supports_parallel_tasks=False,
            sandbox_requirements={"filesystem_access": True, "network_access": True},
            metadata={
                "cli_path": self._cli_path,
                "supports_file_editing": True,
                "supports_terminal_commands": True,
            },
        )

    async def _launch_impl(self) -> None:
        """Verify that the Claude CLI is available."""
        try:
            proc = await asyncio.create_subprocess_exec(
                self._cli_path, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate(timeout=10)
            if proc.returncode != 0:
                raise RuntimeError(f"Claude CLI check failed: {stderr.decode()}")
            logger.info("Claude Code CLI found: %s", stdout.decode().strip())
        except FileNotFoundError:
            raise RuntimeError(
                f"Claude CLI not found at '{self._cli_path}'. "
                "Install it with 'npm install -g @anthropic-ai/claude-code'"
            )

    async def _execute_impl(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute a task using Claude Code CLI.

        Args:
            request: The execution request.

        Returns:
            ExecutionResult with Claude Code's output.
        """
        workspace = self.create_workspace(request.task_id)
        prompt = self._build_prompt(request)

        try:
            # Write the prompt to a file for Claude Code to read
            prompt_file = workspace / "prompt.md"
            prompt_file.write_text(prompt, encoding="utf-8")

            # Execute Claude Code with the prompt
            proc = await asyncio.create_subprocess_exec(
                self._cli_path, "-p", prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(workspace),
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=request.timeout_seconds or 300,
            )

            output = stdout.decode("utf-8", errors="replace")
            error_output = stderr.decode("utf-8", errors="replace")

            if proc.returncode != 0:
                return ExecutionResult(
                    task_id=request.task_id,
                    success=False,
                    output=output,
                    error_type=ExecutionErrorType.INTERNAL_ERROR,
                    error_message=error_output or f"Claude Code exited with code {proc.returncode}",
                )

            return ExecutionResult(
                task_id=request.task_id,
                success=True,
                output=output,
                metadata={"workspace": str(workspace), "return_code": proc.returncode},
            )
        except asyncio.TimeoutError:
            return ExecutionResult(
                task_id=request.task_id,
                success=False,
                error_type=ExecutionErrorType.TIMEOUT,
                error_message=f"Claude Code execution timed out after {request.timeout_seconds}s",
            )
        except Exception as exc:
            return ExecutionResult(
                task_id=request.task_id,
                success=False,
                error_type=ExecutionErrorType.INTERNAL_ERROR,
                error_message=str(exc),
            )

    async def _cancel_impl(self, task_id: str) -> None:
        """Cancel a running Claude Code process.

        Args:
            task_id: The task identifier to cancel.
        """
        if self._process and self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._process.kill()
            self._process = None

    def _build_prompt(self, request: ExecutionRequest) -> str:
        """Build a prompt for Claude Code.

        Args:
            request: The execution request.

        Returns:
            Formatted prompt string.
        """
        parts: list[str] = []

        # Goal
        parts.append(f"# Task\n{request.goal}")

        # Context
        context_str = request.context.get("context", "")
        if context_str:
            parts.append(f"# Context\n{context_str}")

        # Constraints
        if request.constraints:
            parts.append("# Constraints\n" + "\n".join(f"- {c}" for c in request.constraints))

        # Artifact references
        if request.artifacts:
            parts.append("# Referenced Files\n" + "\n".join(
                f"- {a.name}" for a in request.artifacts
            ))

        return "\n\n".join(parts)
