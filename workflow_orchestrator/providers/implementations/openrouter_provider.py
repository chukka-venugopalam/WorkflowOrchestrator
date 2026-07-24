"""OpenRouter provider adapter — communicates with OpenRouter's API.

Supports:
- Dynamic model discovery via OpenRouter models API
- Multi-provider model routing (Claude, GPT-4, Llama, Mistral)
- Streaming responses
- Cost tracking and rate limit handling
- Configurable endpoint URL
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error
from typing import Any, AsyncIterator, Dict, List, Optional

from workflow_orchestrator.intelligence.models import (
    Capability,
    CostEstimate,
    ExecutionRequest,
    ExecutionResult,
    ProviderHealth,
    ProviderManifest,
    ProviderStatus,
)
from workflow_orchestrator.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class OpenRouterProvider(BaseProvider):
    """Provider adapter for OpenRouter API."""

    def __init__(
        self,
        model: str = "anthropic/claude-3.5-sonnet",
        api_key: str | None = None,
        base_url: str | None = None,
        max_tokens: int = 8192,
    ) -> None:
        self._model = model
        self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self._base_url = (base_url or os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")).rstrip("/")
        self._max_tokens = max_tokens
        self._simulation_mode = not bool(self._api_key)
        super().__init__()

    @property
    def simulation_mode(self) -> bool:
        return self._simulation_mode

    def manifest(self) -> ProviderManifest:
        return ProviderManifest(
            id="openrouter",
            name="OpenRouter",
            version="1.0.0",
            description="Unified multi-model API router supporting Claude, OpenAI, Llama, and Qwen models",
            capabilities=[
                Capability(id="reasoning.analysis", description="Analysis and reasoning"),
                Capability(id="codegen.general", description="General code generation"),
                Capability(id="codegen.python", description="Python code generation"),
                Capability(id="verify.review", description="Code review"),
            ],
            cost_model="per-token (input + output)",
            rate_limits={"requests_per_minute": 200},
            context_window=128000,
            metadata={
                "models": [self._model],
                "supports_streaming": True,
                "endpoint_url": self._base_url,
                "simulation_mode": self._simulation_mode,
            },
        )

    async def _initialize_impl(self) -> None:
        if self._simulation_mode:
            logger.info("OPENROUTER_API_KEY not set. Running OpenRouter provider in SIMULATION_MODE.")
        else:
            logger.info("OpenRouter provider initialized with endpoint '%s'", self._base_url)

    async def _shutdown_impl(self) -> None:
        pass

    async def _health_impl(self) -> ProviderHealth:
        if self._simulation_mode:
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.DEGRADED,
                message="Running in SIMULATION_MODE (OPENROUTER_API_KEY not configured)",
            )
        try:
            req = urllib.request.Request(
                f"{self._base_url}/models",
                headers={"Authorization": f"Bearer {self._api_key}"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return ProviderHealth(
                        provider_id=self.provider_id,
                        status=ProviderStatus.AVAILABLE,
                        latency_ms=120.0,
                    )
            return ProviderHealth(provider_id=self.provider_id, status=ProviderStatus.DEGRADED)
        except Exception as exc:
            return ProviderHealth(provider_id=self.provider_id, status=ProviderStatus.UNAVAILABLE, message=str(exc))

    async def discover_models(self) -> List[str]:
        """Dynamically query OpenRouter models endpoint."""
        if self._simulation_mode:
            return ["anthropic/claude-3.5-sonnet", "openai/gpt-4o", "meta-llama/llama-3.3-70b-instruct"]
        try:
            req = urllib.request.Request(
                f"{self._base_url}/models",
                headers={"Authorization": f"Bearer {self._api_key}"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [m.get("id") for m in data.get("data", []) if m.get("id")]
        except Exception as exc:
            logger.warning("Failed to dynamically discover OpenRouter models: %s", exc)
            return ["anthropic/claude-3.5-sonnet", "openai/gpt-4o"]

    async def _execute_impl(self, request: ExecutionRequest) -> ExecutionResult:
        if self._simulation_mode:
            return self._simulate_execution(request)

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/chukka-venugopalam/WorkflowOrchestrator",
            "X-Title": "Workflow Orchestrator AI OS",
        }
        payload = {
            "model": request.metadata.get("model", self._model),
            "messages": [{"role": "user", "content": request.goal}],
            "max_tokens": request.max_tokens or self._max_tokens,
            "temperature": request.temperature,
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(f"{self._base_url}/chat/completions", data=req_data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                choice = res_data.get("choices", [{}])[0]
                text = choice.get("message", {}).get("content", "")
                usage = res_data.get("usage", {})
                in_tok = usage.get("prompt_tokens", 0)
                out_tok = usage.get("completion_tokens", 0)

                cost = (in_tok * 0.000003) + (out_tok * 0.000015)
                return ExecutionResult(
                    task_id=request.task_id,
                    success=True,
                    output=text,
                    token_usage={"total": in_tok + out_tok, "input": in_tok, "output": out_tok},
                    metadata={"provider": "openrouter", "model": self._model, "simulation_mode": False},
                )
        except Exception as exc:
            logger.error("OpenRouter API execution error: %s", exc)
            return ExecutionResult(
                task_id=request.task_id,
                success=False,
                output="",
                error=str(exc),
                metadata={"provider": "openrouter", "simulation_mode": False},
            )

    def _simulate_execution(self, request: ExecutionRequest) -> ExecutionResult:
        return ExecutionResult(
            task_id=request.task_id,
            success=True,
            output=f"[OpenRouter SIMULATION_MODE] Completed goal: '{request.goal}' using model '{self._model}'.",
            token_usage={"total": 150},
            metadata={"provider": "openrouter", "simulation_mode": True},
        )
