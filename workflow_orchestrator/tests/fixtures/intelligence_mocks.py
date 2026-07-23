"""Shared mock provider and agent classes for intelligence layer tests.

These mocks implement IProvider and IAgent interfaces with
configurable capabilities, making them reusable across all
intelligence layer tests.
"""

from __future__ import annotations

from workflow_orchestrator.intelligence.provider import IProvider
from workflow_orchestrator.intelligence.agent import IAgent
from workflow_orchestrator.intelligence.models import (
    AgentManifest,
    AgentStatus,
    Capability,
    CostEstimate,
    ExecutionRequest,
    ExecutionResult,
    ProviderHealth,
    ProviderManifest,
    ProviderStatus,
)


class MockProvider(IProvider):
    """A mock provider for testing with configurable capabilities."""

    def __init__(self, provider_id: str, capabilities: list[str] | None = None) -> None:
        self._id = provider_id
        self._caps = [Capability(id=c) for c in (capabilities or [])]
        self.initialized = False
        self.shut_down = False

    async def initialize(self) -> None:
        self.initialized = True

    async def shutdown(self) -> None:
        self.shut_down = True

    def manifest(self) -> ProviderManifest:
        return ProviderManifest(
            id=self._id,
            name=f"Mock {self._id}",
            version="1.0.0",
            capabilities=self._caps,
        )

    async def capabilities(self) -> list[Capability]:
        return self._caps

    async def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self._id,
            status=ProviderStatus.AVAILABLE,
            latency_ms=100.0,
            error_rate=0.0,
            last_checked="2026-01-01T00:00:00",
            message="Healthy",
        )

    async def submit(self, request: ExecutionRequest) -> ExecutionResult:
        return ExecutionResult(task_id=request.task_id, success=True, output="mock")

    async def stream(self, request: ExecutionRequest):
        yield ExecutionResult(task_id=request.task_id, success=True, output="mock")

    async def cancel(self, task_id: str) -> None:
        pass

    async def status(self, task_id: str) -> ExecutionResult:
        return ExecutionResult(task_id=task_id, success=True)

    async def estimate_cost(self, request: ExecutionRequest) -> CostEstimate:
        return CostEstimate(provider_id=self._id, estimated_cost=0.01)

    async def estimate_latency(self, request: ExecutionRequest) -> float:
        return 100.0


class MockAgent(IAgent):
    """A mock agent for testing with configurable capabilities."""

    def __init__(self, agent_id: str, capabilities: list[str] | None = None) -> None:
        self._id = agent_id
        self._caps = [Capability(id=c) for c in (capabilities or [])]
        self.launched = False
        self.shut_down = False

    async def launch(self) -> None:
        self.launched = True

    async def shutdown(self) -> None:
        self.shut_down = True

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        return ExecutionResult(task_id=request.task_id, success=True, output="mock")

    async def cancel(self, task_id: str) -> None:
        pass

    async def resume(self, task_id: str) -> ExecutionResult:
        return ExecutionResult(task_id=task_id, success=True)

    async def status(self, task_id: str) -> ExecutionResult:
        return ExecutionResult(task_id=task_id, success=True)

    async def heartbeat(self, task_id: str) -> AgentStatus:
        return AgentStatus.IDLE

    def manifest(self) -> AgentManifest:
        return AgentManifest(
            id=self._id,
            name=f"Mock {self._id}",
            version="1.0.0",
            capabilities=self._caps,
        )

    async def supported_capabilities(self) -> list[Capability]:
        return self._caps
