"""Gemini provider adapter — communicates with Google's Gemini API.

Supports Gemini 1.5 Pro, Gemini 1.5 Flash models, streaming,
and multi-modal input. Configuration via environment variable
``GEMINI_API_KEY``.
"""

from __future__ import annotations

import logging
import os
from typing import Any, AsyncIterator, Optional

from workflow_orchestrator.intelligence.models import (
    Capability,
    CostEstimate,
    ExecutionErrorType,
    ExecutionRequest,
    ExecutionResult,
    ProviderHealth,
    ProviderManifest,
    ProviderStatus,
)
from workflow_orchestrator.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    """Provider adapter for Google's Gemini API.

    Capabilities:
    - reasoning.analysis, reasoning.code-review, reasoning.architecture
    - codegen.general, codegen.python, codegen.typescript, codegen.web
    - verify.review
    """

    def __init__(
        self,
        model: str = "gemini-1.5-pro",
        api_key: str | None = None,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        max_tokens: int = 8192,
    ) -> None:
        """Initialize the Gemini provider.

        Args:
            model: Gemini model identifier.
            api_key: Google API key (defaults to GEMINI_API_KEY env var).
            base_url: Base URL for the API.
            max_tokens: Maximum output tokens.
        """
        super().__init__()
        self._model = model
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._max_tokens = max_tokens
        self._http_client: Any = None

    # ------------------------------------------------------------------
    # Manifest
    # ------------------------------------------------------------------

    def manifest(self) -> ProviderManifest:
        """Get the provider's declared manifest."""
        return ProviderManifest(
            id="google.gemini",
            name="Gemini (Google)",
            version="3.0.0",
            description="Google's Gemini models — supports reasoning, code generation, and multi-modal analysis",
            capabilities=[
                Capability(id="reasoning.analysis", description="Deep analysis and reasoning"),
                Capability(id="reasoning.code-review", description="Code review and quality analysis"),
                Capability(id="reasoning.architecture", description="Architecture design and evaluation"),
                Capability(id="codegen.general", description="General code generation"),
                Capability(id="codegen.python", description="Python code generation"),
                Capability(id="codegen.typescript", description="TypeScript/JavaScript code generation"),
                Capability(id="codegen.web", description="Web development (HTML, CSS, JS)"),
                Capability(id="verify.review", description="Code review and verification"),
            ],
            cost_model="per-token (input + output)",
            rate_limits={
                "tokens_per_minute": 36000,
                "requests_per_minute": 360,
            },
            context_window=1000000,
            metadata={
                "models": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"],
                "supports_streaming": True,
                "supports_multi_modal": True,
                "supports_code_execution": True,
            },
        )

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    async def _initialize_impl(self) -> None:
        """Initialize the HTTP client for Gemini API."""
        if not self._api_key:
            logger.warning("GEMINI_API_KEY not set. Gemini provider may fail on execution.")
        try:
            import httpx
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={"content-type": "application/json"},
                params={"key": self._api_key},
                timeout=httpx.Timeout(120.0),
            )
            logger.debug("Gemini HTTP client initialized for model '%s'", self._model)
        except ImportError:
            logger.warning("httpx not installed. Gemini provider will use simulated mode.")
            self._http_client = None

    async def _shutdown_impl(self) -> None:
        """Close the HTTP client."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def _health_impl(self) -> ProviderHealth:
        """Check Gemini API health."""
        if self._http_client is None:
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.DEGRADED,
                message="HTTP client not available",
            )
        try:
            response = await self._http_client.get("/models")
            if response.status_code < 500:
                return ProviderHealth(
                    provider_id=self.provider_id,
                    status=ProviderStatus.AVAILABLE,
                    message="API is responsive",
                )
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.DEGRADED,
                message=f"API returned status {response.status_code}",
            )
        except Exception as exc:
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.UNAVAILABLE,
                message=str(exc),
            )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def _execute_impl(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute a request against the Gemini API.

        Args:
            request: The execution request.

        Returns:
            ExecutionResult with Gemini's response.
        """
        if self._http_client is None:
            return self._simulate_execution(request)

        contents = self._build_contents(request)
        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": request.max_tokens or self._max_tokens,
                "temperature": request.temperature,
            },
        }

        system_instruction = self._build_system_instruction(request)
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        try:
            url = f"/models/{self._model}:generateContent"
            response = await self._http_client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            output_text = ""
            for candidate in data.get("candidates", []):
                for part in candidate.get("content", {}).get("parts", []):
                    output_text += part.get("text", "")

            usage = data.get("usageMetadata", {})
            return ExecutionResult(
                task_id=request.task_id,
                success=True,
                output=output_text,
                token_usage={
                    "input": usage.get("promptTokenCount", 0),
                    "output": usage.get("candidatesTokenCount", 0),
                    "total": usage.get("totalTokenCount", 0),
                },
                cost=CostEstimate(
                    provider_id=self.provider_id,
                    estimated_cost=0.0,
                    currency="USD",
                    confidence=0.7,
                ),
                metadata={"model": self._model, "finish_reason": data.get("candidates", [{}])[0].get("finishReason", "")},
            )
        except Exception as exc:
            logger.error("Gemini API request failed: %s", exc)
            return ExecutionResult(
                task_id=request.task_id,
                success=False,
                error_type=ExecutionErrorType.INTERNAL_ERROR,
                error_message=str(exc),
            )

    async def _stream_impl(self, request: ExecutionRequest) -> AsyncIterator[ExecutionResult]:
        """Stream a response from the Gemini API.

        Args:
            request: The execution request.

        Yields:
            Partial ExecutionResult objects.
        """
        if self._http_client is None:
            yield await self._simulate_execution(request)
            return

        contents = self._build_contents(request)
        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": request.max_tokens or self._max_tokens,
                "temperature": request.temperature,
            },
        }

        system_instruction = self._build_system_instruction(request)
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        try:
            url = f"/models/{self._model}:streamGenerateContent"
            full_text = ""
            async with self._http_client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        import json
                        data = json.loads(line[6:])
                        for candidate in data.get("candidates", []):
                            for part in candidate.get("content", {}).get("parts", []):
                                text = part.get("text", "")
                                if text:
                                    full_text += text
                                    yield ExecutionResult(
                                        task_id=request.task_id,
                                        success=False,
                                        output=text,
                                        metadata={"streaming": True, "partial": True},
                                    )

            yield ExecutionResult(
                task_id=request.task_id,
                success=True,
                output=full_text,
                metadata={"model": self._model, "streaming": True},
            )
        except Exception as exc:
            logger.error("Gemini streaming request failed: %s", exc)
            yield ExecutionResult(
                task_id=request.task_id,
                success=False,
                error_type=ExecutionErrorType.INTERNAL_ERROR,
                error_message=str(exc),
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_contents(self, request: ExecutionRequest) -> list[dict[str, Any]]:
        """Build the contents array for the Gemini API.

        Args:
            request: The execution request.

        Returns:
            List of content dictionaries.
        """
        contents: list[dict[str, Any]] = []

        for entry in request.context.get("history", []):
            role = entry.get("role", "user")
            content = entry.get("content", "")
            gemini_role = "model" if role == "assistant" else "user"
            contents.append({"role": gemini_role, "parts": [{"text": content}]})

        # Build user message
        user_text = request.goal
        if request.artifacts:
            artifact_text = "\n".join(f"- {a.name} ({a.content_type})" for a in request.artifacts)
            user_text = f"{user_text}\n\nReferenced artifacts:\n{artifact_text}"
        if request.constraints:
            constraints_text = "\n".join(f"- {c}" for c in request.constraints)
            user_text = f"{user_text}\n\nConstraints:\n{constraints_text}"

        contents.append({"role": "user", "parts": [{"text": user_text}]})
        return contents

    def _build_system_instruction(self, request: ExecutionRequest) -> str:
        """Build the system instruction.

        Args:
            request: The execution request.

        Returns:
            System instruction string.
        """
        parts: list[str] = []
        context_str = request.context.get("context", "")
        if context_str:
            parts.append(f"Context:\n{context_str}")
        capability_desc = request.capability.description if request.capability else ""
        if capability_desc:
            parts.append(f"Focus: {capability_desc}")
        return "\n\n".join(parts)

    def _simulate_execution(self, request: ExecutionRequest) -> ExecutionResult:
        """Simulate execution when no API client is available.

        Args:
            request: The execution request.

        Returns:
            Simulated ExecutionResult.
        """
        logger.info("Gemini provider running in simulated mode for task '%s'", request.task_id)
        return ExecutionResult(
            task_id=request.task_id,
            success=True,
            output=f"[Gemini Simulation - {self._model}]\n"
                   f"Goal: {request.goal}\n\n"
                   f"This is a simulated response. Install 'httpx' and set GEMINI_API_KEY "
                   f"to connect to the real Gemini API.",
            token_usage={"input": 50, "output": 100},
            cost=CostEstimate(
                provider_id=self.provider_id,
                estimated_cost=0.0,
                currency="USD",
                confidence=0.0,
            ),
            metadata={"simulated": True, "model": self._model},
        )
