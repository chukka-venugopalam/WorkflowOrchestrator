"""Claude provider adapter — communicates with Anthropic's Claude API.

This provider supports:
- Claude 3 Opus, Sonnet, and Haiku models
- Streaming responses
- System prompts and multi-turn conversations
- Tool/function calling
- Vision (image input)

Configuration via environment variable ``ANTHROPIC_API_KEY``.
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


class ClaudeProvider(BaseProvider):
    """Provider adapter for Anthropic's Claude API.

    Capabilities:
    - reasoning.analysis, reasoning.code-review, reasoning.architecture
    - codegen.general, codegen.python, codegen.typescript, codegen.web
    - verify.review
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str | None = None,
        base_url: str = "https://api.anthropic.com/v1",
        max_tokens: int = 8192,
    ) -> None:
        """Initialize the Claude provider.

        Args:
            model: Claude model identifier.
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var).
            base_url: Base URL for the API.
            max_tokens: Maximum output tokens.
        """
        super().__init__()
        self._model = model
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._max_tokens = max_tokens
        self._http_client: Any = None

    # ------------------------------------------------------------------
    # Manifest
    # ------------------------------------------------------------------

    def manifest(self) -> ProviderManifest:
        """Get the provider's declared manifest."""
        return ProviderManifest(
            id="anthropic.claude",
            name="Claude (Anthropic)",
            version="3.0.0",
            description="Anthropic's Claude AI assistant — supports reasoning, code generation, and analysis",
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
                "tokens_per_minute": 200000,
                "requests_per_minute": 1000,
            },
            context_window=200000,
            metadata={
                "models": ["claude-sonnet-4-20250514", "claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
                "supports_streaming": True,
                "supports_tools": True,
                "supports_vision": True,
            },
        )

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    async def _initialize_impl(self) -> None:
        """Initialize the HTTP client for Claude API."""
        if not self._api_key:
            logger.warning("ANTHROPIC_API_KEY not set. Claude provider may fail on execution.")
        try:
            import httpx
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                timeout=httpx.Timeout(self._max_tokens // 100 + 30),
            )
            logger.debug("Claude HTTP client initialized for model '%s'", self._model)
        except ImportError:
            logger.warning("httpx not installed. Claude provider will use simulated mode.")
            self._http_client = None

    async def _shutdown_impl(self) -> None:
        """Close the HTTP client."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def _health_impl(self) -> ProviderHealth:
        """Check Claude API health by querying the models endpoint."""
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
                    latency_ms=response.elapsed.total_seconds() * 1000 if hasattr(response, "elapsed") else 0,
                    last_checked=__import__("datetime").datetime.now(
                        __import__("datetime").timezone.utc
                    ).isoformat(),
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
        """Execute a request against the Claude API.

        Args:
            request: The execution request with goal and context.

        Returns:
            ExecutionResult with Claude's response.
        """
        if self._http_client is None:
            return self._simulate_execution(request)

        # Build the request payload
        messages = self._build_messages(request)
        payload = {
            "model": self._model,
            "max_tokens": request.max_tokens or self._max_tokens,
            "messages": messages,
            "temperature": request.temperature,
        }

        # Add system prompt if context is available
        system_prompt = self._build_system_prompt(request)
        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = await self._http_client.post("/messages", json=payload)
            response.raise_for_status()
            data = response.json()

            output_text = ""
            input_tokens = 0
            output_tokens = 0

            for content_block in data.get("content", []):
                if content_block.get("type") == "text":
                    output_text += content_block.get("text", "")

            usage = data.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

            return ExecutionResult(
                task_id=request.task_id,
                success=True,
                output=output_text,
                token_usage={"input": input_tokens, "output": output_tokens},
                cost=CostEstimate(
                    provider_id=self.provider_id,
                    estimated_cost=self._estimate_cost_from_tokens(input_tokens, output_tokens),
                    currency="USD",
                    confidence=0.9,
                ),
                metadata={"model": self._model, "stop_reason": data.get("stop_reason", "")},
            )
        except Exception as exc:
            logger.error("Claude API request failed: %s", exc)
            return ExecutionResult(
                task_id=request.task_id,
                success=False,
                error_type=ExecutionErrorType.INTERNAL_ERROR,
                error_message=str(exc),
            )

    async def _stream_impl(self, request: ExecutionRequest) -> AsyncIterator[ExecutionResult]:
        """Stream a response from the Claude API.

        Args:
            request: The execution request.

        Yields:
            Partial ExecutionResult objects with streaming content.
        """
        if self._http_client is None:
            result = self._simulate_execution(request)
            yield result
            return

        messages = self._build_messages(request)
        payload = {
            "model": self._model,
            "max_tokens": request.max_tokens or self._max_tokens,
            "messages": messages,
            "temperature": request.temperature,
            "stream": True,
        }

        system_prompt = self._build_system_prompt(request)
        if system_prompt:
            payload["system"] = system_prompt

        try:
            full_text = ""
            input_tokens = 0
            output_tokens = 0

            async with self._http_client.stream("POST", "/messages", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        import json
                        data = json.loads(line[6:])
                        if data.get("type") == "content_block_delta":
                            delta = data.get("delta", {})
                            text = delta.get("text", "")
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
                token_usage={"input": input_tokens, "output": output_tokens},
                cost=CostEstimate(
                    provider_id=self.provider_id,
                    estimated_cost=self._estimate_cost_from_tokens(input_tokens, output_tokens),
                    currency="USD",
                    confidence=0.9,
                ),
                metadata={"model": self._model, "streaming": True},
            )
        except Exception as exc:
            logger.error("Claude streaming request failed: %s", exc)
            yield ExecutionResult(
                task_id=request.task_id,
                success=False,
                error_type=ExecutionErrorType.INTERNAL_ERROR,
                error_message=str(exc),
            )

    async def _estimate_cost_impl(self, request: ExecutionRequest) -> CostEstimate:
        """Estimate the cost of a request.

        Args:
            request: The execution request.

        Returns:
            CostEstimate with estimated cost.
        """
        estimated_input = len(request.goal) + len(str(request.context))
        estimated_output = request.max_tokens or self._max_tokens
        return CostEstimate(
            provider_id=self.provider_id,
            estimated_cost=self._estimate_cost_from_tokens(estimated_input // 4, estimated_output),
            currency="USD",
            confidence=0.5,
            breakdown={"input_tokens": estimated_input // 4, "output_tokens": estimated_output},
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_messages(self, request: ExecutionRequest) -> list[dict[str, Any]]:
        """Build the messages array for the Claude API.

        Args:
            request: The execution request.

        Returns:
            List of message dictionaries.
        """
        messages: list[dict[str, Any]] = []

        # Add execution history as messages
        for entry in request.context.get("history", []):
            role = entry.get("role", "user")
            content = entry.get("content", "")
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": content})

        # Add artifact references as context
        artifact_context = ""
        for art in request.artifacts:
            if art.name:
                artifact_context += f"\n--- {art.name} ({art.content_type}) ---\n"
                if art.uri:
                    artifact_context += f"URI: {art.uri}\n"

        # Add constraints
        constraints_text = ""
        if request.constraints:
            constraints_text = "\n".join(f"- {c}" for c in request.constraints)

        # Build the user message
        user_content = request.goal
        if artifact_context:
            user_content = f"{request.goal}\n\nReferenced artifacts:\n{artifact_context}"
        if constraints_text:
            user_content = f"{user_content}\n\nConstraints:\n{constraints_text}"

        messages.append({"role": "user", "content": user_content})
        return messages

    def _build_system_prompt(self, request: ExecutionRequest) -> str:
        """Build the system prompt from context.

        Args:
            request: The execution request.

        Returns:
            System prompt string.
        """
        parts: list[str] = []

        goal = request.context.get("goal", request.goal)
        context_str = request.context.get("context", "")
        capability = request.capability.id if request.capability else "general"

        if context_str:
            parts.append(f"Context:\n{context_str}")

        parts.append(f"You are an expert AI assistant. Focus on: {goal}")
        parts.append(f"Capability: {capability}")

        return "\n\n".join(parts)

    def _estimate_cost_from_tokens(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost based on token usage and model pricing.

        Args:
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD.
        """
        # Claude Sonnet pricing (approximate)
        input_rate = 3.0 / 1_000_000  # $3 per million input tokens
        output_rate = 15.0 / 1_000_000  # $15 per million output tokens
        return (input_tokens * input_rate) + (output_tokens * output_rate)

    def _simulate_execution(self, request: ExecutionRequest) -> ExecutionResult:
        """Simulate execution when no API client is available.

        Args:
            request: The execution request.

        Returns:
            Simulated ExecutionResult.
        """
        logger.info("Claude provider running in simulated mode for task '%s'", request.task_id)
        return ExecutionResult(
            task_id=request.task_id,
            success=True,
            output=f"[Claude Simulation - {self._model}]\n"
                   f"Goal: {request.goal}\n\n"
                   f"This is a simulated response. Install 'httpx' and set ANTHROPIC_API_KEY "
                   f"to connect to the real Claude API.\n\n"
                   f"Capability: {request.capability.id if request.capability else 'general'}\n"
                   f"Temperature: {request.temperature}\n"
                   f"Max tokens: {request.max_tokens or self._max_tokens}",
            token_usage={"input": 50, "output": 100},
            cost=CostEstimate(
                provider_id=self.provider_id,
                estimated_cost=0.001,
                currency="USD",
                confidence=0.0,
            ),
            metadata={"simulated": True, "model": self._model},
        )
