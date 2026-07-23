"""GitHub Copilot agent adapter — communicates with GitHub Copilot API.

GitHub Copilot provides AI-powered code completion and chat.
This adapter uses the Copilot API for code generation tasks.
"""

from __future__ import annotations

import logging
import os
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


class GitHubCopilotAgent(BaseAgent):
    """Agent adapter for GitHub Copilot.

    GitHub Copilot provides AI-powered code completion and chat
    through GitHub's API. Requires GitHub token with Copilot access.

    Requires ``GITHUB_TOKEN`` environment variable with Copilot license.
    """

    def __init__(
        self,
        github_token: str | None = None,
        base_url: str = "https://api.githubcopilot.com",
        workspace_base: str | None = None,
    ) -> None:
        """Initialize the GitHub Copilot agent.

        Args:
            github_token: GitHub token (defaults to GITHUB_TOKEN env var).
            base_url: Base URL for Copilot API.
            workspace_base: Base directory for agent workspaces.
        """
        super().__init__(workspace_base=workspace_base)
        self._github_token = github_token or os.environ.get("GITHUB_TOKEN", "")
        self._base_url = base_url.rstrip("/")
        self._http_client: Any = None

    def manifest(self) -> AgentManifest:
        """Get the agent's declared manifest."""
        return AgentManifest(
            id="github-copilot",
            name="GitHub Copilot",
            version="1.0.0",
            description="GitHub Copilot — AI-powered code completion and chat agent",
            capabilities=[
                Capability(id="codegen.general", description="General code generation"),
                Capability(id="codegen.python", description="Python code generation"),
                Capability(id="codegen.typescript", description="TypeScript/JavaScript code generation"),
                Capability(id="codegen.web", description="Web development (HTML, CSS, JS)"),
                Capability(id="reasoning.code-review", description="Code review and quality analysis"),
            ],
            requires_local_runtime=False,
            supports_parallel_tasks=True,
            metadata={
                "supports_completion": True,
                "supports_chat": True,
                "requires_github_token": True,
            },
        )

    async def _launch_impl(self) -> None:
        """Verify Copilot API availability."""
        if not self._github_token:
            logger.warning("GITHUB_TOKEN not set. GitHub Copilot agent may fail on execution.")
        try:
            import httpx
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "authorization": f"Bearer {self._github_token}",
                    "content-type": "application/json",
                    "copilot-integration-id": "workflow-orchestrator",
                },
                timeout=httpx.Timeout(60.0),
            )
        except ImportError:
            logger.warning("httpx not installed. Copilot agent will use simulated mode.")
            self._http_client = None

    async def _shutdown_impl(self) -> None:
        """Close the HTTP client."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def _execute_impl(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute a task using GitHub Copilot API.

        Args:
            request: The execution request.

        Returns:
            ExecutionResult with Copilot's output.
        """
        if self._http_client is None:
            return self._simulate_execution(request)

        payload = {
            "model": "gpt-4o-copilot",
            "messages": [
                {"role": "system", "content": "You are GitHub Copilot, an expert coding assistant."},
                {"role": "user", "content": request.goal},
            ],
            "max_tokens": request.max_tokens or 4096,
        }

        try:
            response = await self._http_client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            return ExecutionResult(
                task_id=request.task_id,
                success=True,
                output=data.get("choices", [{}])[0].get("message", {}).get("content", ""),
                metadata={"model": data.get("model", "gpt-4o-copilot")},
            )
        except Exception as exc:
            logger.error("Copilot API request failed: %s", exc)
            return ExecutionResult(
                task_id=request.task_id,
                success=False,
                error_type=ExecutionErrorType.INTERNAL_ERROR,
                error_message=str(exc),
            )

    def _simulate_execution(self, request: ExecutionRequest) -> ExecutionResult:
        """Simulate execution when no API client is available.

        Args:
            request: The execution request.

        Returns:
            Simulated ExecutionResult.
        """
        logger.info("GitHub Copilot agent running in simulated mode for task '%s'", request.task_id)
        return ExecutionResult(
            task_id=request.task_id,
            success=True,
            output=f"[GitHub Copilot Simulation]\nGoal: {request.goal}\n\n"
                   f"This is a simulated response. Set GITHUB_TOKEN to connect to the real Copilot API.",
            metadata={"simulated": True},
        )
