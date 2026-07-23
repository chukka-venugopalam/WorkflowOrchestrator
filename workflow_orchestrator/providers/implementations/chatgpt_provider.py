"""ChatGPT/OpenAI provider adapter — communicates with OpenAI's API.

Supports GPT-4, GPT-4o, GPT-3.5 models, streaming, function calling,
and vision. Configuration via environment variable ``OPENAI_API_KEY``.
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


class ChatGPTProvider(BaseProvider):
    """Provider adapter for OpenAI's API (ChatGPT models).

    Capabilities:
    - reasoning.analysis, reasoning.code-review, reasoning.architecture
    - codegen.general, codegen.python, codegen.typescript, codegen.web
    - verify.review
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        max_tokens: int = 4096,
    ) -> None:
        """Initialize the ChatGPT provider.

        Args:
            model: OpenAI model identifier.
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var).
            base_url: Base URL for the API.
            max_tokens: Maximum output tokens.
        """
        super().__init__()
        self._model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._max_tokens = max_tokens
        self._http_client: Any = None

    # ------------------------------------------------------------------
    # Manifest
    # ------------------------------------------------------------------

    def manifest(self) -> ProviderManifest:
        """Get the provider's declared manifest."""
        return ProviderManifest(
            id="openai.chatgpt",
            name="ChatGPT (OpenAI)",
            version="3.0.0",
            description="OpenAI's GPT models — supports reasoning, code generation, and analysis",
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
                "tokens_per_minute": 500000,
                "requests_per_minute": 5000,
            },
            context_window=128000,
            metadata={
                "models": ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
                "supports_streaming": True,
                "supports_functions": True,
                "supports_vision": True,
            },
        )

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    async def _initialize_impl(self) -> None:
        """Initialize the HTTP client for OpenAI API."""
        if not self._api_key:
            logger.warning("OPENAI_API_KEY not set. ChatGPT provider may fail on execution.")
        try:
            import httpx
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "authorization": f"Bearer {self._api_key}",
                    "content-type": "application/json",
                },
                timeout=httpx.Timeout(120.0),
            )
            logger.debug("ChatGPT HTTP client initialized for model '%s'", self._model)
        except ImportError:
            logger.warning("httpx not installed. ChatGPT provider will use simulated mode.")
            self._http_client = None

    async def _shutdown_impl(self) -> None:
        """Close the HTTP client."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def _health_impl(self) -> ProviderHealth:
        """Check OpenAI API health."""
        if self._http_client is None:
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.DEGRADED,
                message="HTTP client not available (httpx not installed)",
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
        """Execute a request against the OpenAI API.

        Args:
            request: The execution request.

        Returns:
            ExecutionResult with model response.
        """
        if self._http_client is None:
            return self._simulate_execution(request)

        messages = self._build_messages(request)
        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": request.max_tokens or self._max_tokens,
            "temperature": request.temperature,
        }

        try:
            response = await self._http_client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            output_text = message.get("content", "")
            usage = data.get("usage", {})

            return ExecutionResult(
                task_id=request.task_id,
                success=True,
                output=output_text,
                token_usage={
                    "input": usage.get("prompt_tokens", 0),
                    "output": usage.get("completion_tokens", 0),
                    "total": usage.get("total_tokens", 0),
                },
                cost=CostEstimate(
                    provider_id=self.provider_id,
                    estimated_cost=self._estimate_cost_from_tokens(
                        usage.get("prompt_tokens", 0),
                        usage.get("completion_tokens", 0),
                    ),
                    currency="USD",
                    confidence=0.9,
                ),
                metadata={
                    "model": data.get("model", self._model),
                    "finish_reason": choice.get("finish_reason", ""),
                },
            )
        except Exception as exc:
            logger.error("OpenAI API request failed: %s", exc)
            return ExecutionResult(
                task_id=request.task_id,
                success=False,
                error_type=ExecutionErrorType.INTERNAL_ERROR,
                error_message=str(exc),
            )

    async def _stream_impl(self, request: ExecutionRequest) -> AsyncIterator[ExecutionResult]:
        """Stream a response from the OpenAI API.

        Args:
            request: The execution request.

        Yields:
            Partial ExecutionResult objects.
        """
        if self._http_client is None:
            yield await self._simulate_execution(request)
            return

        messages = self._build_messages(request)
        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": request.max_tokens or self._max_tokens,
            "temperature": request.temperature,
            "stream": True,
        }

        try:
            full_text = ""
            async with self._http_client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and not line.startswith("data: [DONE]"):
                        import json
                        data = json.loads(line[6:])
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        text = delta.get("content", "")
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
            logger.error("OpenAI streaming request failed: %s", exc)
            yield ExecutionResult(
                task_id=request.task_id,
                success=False,
                error_type=ExecutionErrorType.INTERNAL_ERROR,
                error_message=str(exc),
            )

    async def _estimate_cost_impl(self, request: ExecutionRequest) -> CostEstimate:
        """Estimate request cost.

        Args:
            request: The execution request.

        Returns:
            CostEstimate.
        """
        estimated_input = (len(request.goal) + len(str(request.context))) // 4
        estimated_output = request.max_tokens or self._max_tokens
        return CostEstimate(
            provider_id=self.provider_id,
            estimated_cost=self._estimate_cost_from_tokens(estimated_input, estimated_output),
            currency="USD",
            confidence=0.5,
            breakdown={"input_tokens": estimated_input, "output_tokens": estimated_output},
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_messages(self, request: ExecutionRequest) -> list[dict[str, Any]]:
        """Build the messages array for the OpenAI API.

        Args:
            request: The execution request.

        Returns:
            List of message dictionaries.
        """
        messages: list[dict[str, Any]] = []

        # Build system message
        system_parts: list[str] = []
        context_str = request.context.get("context", "")
        if context_str:
            system_parts.append(f"Context:\n{context_str}")
        capability_desc = request.capability.description if request.capability else ""
        if capability_desc:
            system_parts.append(f"Focus: {capability_desc}")
        if system_parts:
            messages.append({"role": "system", "content": "\n\n".join(system_parts)})

        # Add execution history
        for entry in request.context.get("history", []):
            role = entry.get("role", "user")
            content = entry.get("content", "")
            if role in ("user", "assistant", "system"):
                messages.append({"role": role, "content": content})

        # Build user message with artifacts and constraints
        user_content = request.goal
        if request.artifacts:
            artifact_text = "\n".join(f"- {a.name} ({a.content_type})" for a in request.artifacts)
            user_content = f"{user_content}\n\nReferenced artifacts:\n{artifact_text}"
        if request.constraints:
            constraints_text = "\n".join(f"- {c}" for c in request.constraints)
            user_content = f"{user_content}\n\nConstraints:\n{constraints_text}"

        messages.append({"role": "user", "content": user_content})
        return messages

    def _estimate_cost_from_tokens(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost based on token usage.

        Args:
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD.
        """
        # GPT-4o pricing (approximate)
        input_rate = 2.5 / 1_000_000
        output_rate = 10.0 / 1_000_000
        return (input_tokens * input_rate) + (output_tokens * output_rate)

    def _simulate_execution(self, request: ExecutionRequest) -> ExecutionResult:
        """Simulate execution when no API client is available.

        Args:
            request: The execution request.

        Returns:
            Simulated ExecutionResult.
        """
        logger.info("ChatGPT provider running in simulated mode for task '%s'", request.task_id)
        return ExecutionResult(
            task_id=request.task_id,
            success=True,
            output=f"[ChatGPT Simulation - {self._model}]\n"
                   f"Goal: {request.goal}\n\n"
                   f"This is a simulated response. Install 'httpx' and set OPENAI_API_KEY "
                   f"to connect to the real OpenAI API.\n\n"
                   f"Capability: {request.capability.id if request.capability else 'general'}",
            token_usage={"input": 50, "output": 100},
            cost=CostEstimate(
                provider_id=self.provider_id,
                estimated_cost=0.001,
                currency="USD",
                confidence=0.0,
            ),
            metadata={"simulated": True, "model": self._model},
        )
