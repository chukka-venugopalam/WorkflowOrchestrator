"""Cursor agent adapter — communicates with the Cursor editor's AI backend.

Cursor is an AI-powered code editor. This adapter communicates with
Cursor's API for code generation and editing tasks.
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


class CursorAgent(BaseAgent):
    """Agent adapter for Cursor AI editor.

    Cursor provides AI-powered code editing through its editor.
    This adapter communicates with Cursor's API.

    Requires ``CURSOR_API_KEY`` environment variable.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.cursor.com/v1",
        workspace_base: str | None = None,
    ) -> None:
        """Initialize the Cursor agent.

        Args:
            api_key: Cursor API key (defaults to CURSOR_API_KEY env var).
            base_url: Base URL for Cursor API.
            workspace_base: Base directory for agent workspaces.
        """
        super().__init__(workspace_base=workspace_base)
        self._api_key = api_key or os.environ.get("CURSOR_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._http_client: Any = None

    def manifest(self) -> AgentManifest:
        """Get the agent's declared manifest."""
        return AgentManifest(
            id="cursor",
            name="Cursor AI",
            version="1.0.0",
            description="Cursor AI-powered code editor agent for code generation and editing",
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
                "api_url": self._base_url,
                "supports_chat": True,
                "supports_inline_edits": True,
            },
        )

    async def _launch_impl(self) -> None:
        """Verify Cursor API availability."""
        if not self._api_key:
            logger.warning("CURSOR_API_KEY not set. Cursor agent may fail on execution.")
        try:
            import httpx
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "authorization": f"Bearer {self._api_key}",
                    "content-type": "application/json",
                },
                timeout=httpx.Timeout(60.0),
            )
        except ImportError:
            logger.warning("httpx not installed. Cursor agent will use simulated mode.")
            self._http_client = None

    async def _shutdown_impl(self) -> None:
        """Close the HTTP client."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def _execute_impl(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute a task using Cursor API.

        Args:
            request: The execution request.

        Returns:
            ExecutionResult with Cursor's output.
        """
        if self._http_client is None:
            return self._simulate_execution(request)

        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are Cursor AI, an expert coding assistant."},
                {"role": "user", "content": request.goal},
            ],
            "max_tokens": request.max_tokens or 4096,
            "temperature": request.temperature,
        }

        try:
            response = await self._http_client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            return ExecutionResult(
                task_id=request.task_id,
                success=True,
                output=data.get("choices", [{}])[0].get("message", {}).get("content", ""),
                metadata={"model": data.get("model", "gpt-4o")},
            )
        except Exception as exc:
            logger.error("Cursor API request failed: %s", exc)
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
        logger.info("Cursor agent running in simulated mode for task '%s'", request.task_id)
        return ExecutionResult(
            task_id=request.task_id,
            success=True,
            output=f"[Cursor Simulation]\nGoal: {request.goal}\n\n"
                   f"This is a simulated response. Set CURSOR_API_KEY to connect to the real Cursor API.",
            metadata={"simulated": True},
        )
