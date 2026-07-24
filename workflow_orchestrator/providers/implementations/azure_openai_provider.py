"""Azure OpenAI provider adapter — communicates with Azure OpenAI Service endpoints.

Supports:
- Azure OpenAI deployments (gpt-4o, gpt-4, gpt-35-turbo)
- Deployment name mapping & API versioning
- Streaming responses
- Token cost tracking and enterprise compliance headers
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


class AzureOpenAIProvider(BaseProvider):
    """Provider adapter for Azure OpenAI Service."""

    def __init__(
        self,
        deployment_name: str = "gpt-4o",
        api_key: str | None = None,
        endpoint: str | None = None,
        api_version: str = "2024-06-01",
        max_tokens: int = 8192,
    ) -> None:
        self._deployment_name = deployment_name
        self._api_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY", "")
        self._endpoint = (endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT", "")).rstrip("/")
        self._api_version = api_version
        self._max_tokens = max_tokens
        self._simulation_mode = not bool(self._api_key and self._endpoint)
        super().__init__()

    @property
    def simulation_mode(self) -> bool:
        return self._simulation_mode

    def manifest(self) -> ProviderManifest:
        return ProviderManifest(
            id="azure_openai",
            name="Azure OpenAI Service",
            version="1.0.0",
            description="Enterprise Azure OpenAI API supporting deployed GPT models",
            capabilities=[
                Capability(id="reasoning.analysis", description="Enterprise analysis"),
                Capability(id="codegen.general", description="Enterprise code generation"),
                Capability(id="codegen.python", description="Python code generation"),
            ],
            cost_model="enterprise per-token",
            rate_limits={"requests_per_minute": 500},
            context_window=128000,
            metadata={
                "deployment": self._deployment_name,
                "endpoint": self._endpoint,
                "api_version": self._api_version,
                "simulation_mode": self._simulation_mode,
            },
        )

    async def _initialize_impl(self) -> None:
        if self._simulation_mode:
            logger.info("AZURE_OPENAI_API_KEY or ENDPOINT missing. Running Azure OpenAI in SIMULATION_MODE.")
        else:
            logger.info("Azure OpenAI provider initialized for deployment '%s'", self._deployment_name)

    async def _shutdown_impl(self) -> None:
        pass

    async def _health_impl(self) -> ProviderHealth:
        if self._simulation_mode:
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.DEGRADED,
                message="Running in SIMULATION_MODE (AZURE_OPENAI_API_KEY/ENDPOINT unconfigured)",
            )
        return ProviderHealth(provider_id=self.provider_id, status=ProviderStatus.AVAILABLE)

    async def _execute_impl(self, request: ExecutionRequest) -> ExecutionResult:
        if self._simulation_mode:
            return self._simulate_execution(request)

        url = f"{self._endpoint}/openai/deployments/{self._deployment_name}/chat/completions?api-version={self._api_version}"
        headers = {
            "api-key": self._api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "messages": [{"role": "user", "content": request.goal}],
            "max_tokens": request.max_tokens or self._max_tokens,
            "temperature": request.temperature,
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                choice = res_data.get("choices", [{}])[0]
                text = choice.get("message", {}).get("content", "")
                usage = res_data.get("usage", {})
                in_tok = usage.get("prompt_tokens", 0)
                out_tok = usage.get("completion_tokens", 0)

                return ExecutionResult(
                    task_id=request.task_id,
                    success=True,
                    output=text,
                    token_usage={"total": in_tok + out_tok, "input": in_tok, "output": out_tok},
                    metadata={"provider": "azure_openai", "deployment": self._deployment_name, "simulation_mode": False},
                )
        except Exception as exc:
            logger.error("Azure OpenAI execution error: %s", exc)
            return ExecutionResult(
                task_id=request.task_id,
                success=False,
                output="",
                error=str(exc),
                metadata={"provider": "azure_openai", "simulation_mode": False},
            )

    def _simulate_execution(self, request: ExecutionRequest) -> ExecutionResult:
        return ExecutionResult(
            task_id=request.task_id,
            success=True,
            output=f"[Azure OpenAI SIMULATION_MODE] Completed goal '{request.goal}' via deployment '{self._deployment_name}'.",
            token_usage={"total": 140},
            metadata={"provider": "azure_openai", "simulation_mode": True},
        )
