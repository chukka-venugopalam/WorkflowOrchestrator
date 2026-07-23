"""Unit tests for the Intelligence Plane data models."""

from __future__ import annotations

import pytest
from workflow_orchestrator.intelligence.models import (
    Capability,
    ProviderManifest,
    ProviderHealth,
    ProviderStatus,
    AgentManifest,
    AgentStatus,
    ExecutionRequest,
    ExecutionResult,
    ExecutionErrorType,
    ArtifactReference,
    Session,
    SessionState,
    TaskRecord,
    Prompt,
    ContextBundle,
    RoutingDecision,
    RoutingCandidate,
    Plan,
    BudgetAllocation,
    CostEstimate,
)


class TestCapabilityModel:
    def test_valid_capability(self) -> None:
        cap = Capability(id="reasoning.code-review", description="Review code")
        assert cap.id == "reasoning.code-review"
        assert cap.version == "1.0.0"

    def test_invalid_capability_raises(self) -> None:
        with pytest.raises(ValueError, match="namespaced"):
            Capability(id="invalid")


class TestProviderManifest:
    def test_defaults(self) -> None:
        manifest = ProviderManifest(id="test.provider")
        assert manifest.id == "test.provider"
        assert manifest.capabilities == []
        assert not manifest.deprecated


class TestProviderHealth:
    def test_default_status(self) -> None:
        health = ProviderHealth(provider_id="test.provider")
        assert health.status == ProviderStatus.UNINITIALIZED


class TestAgentManifest:
    def test_default_requires_local(self) -> None:
        manifest = AgentManifest(id="test.agent")
        assert manifest.requires_local_runtime


class TestExecutionRequest:
    def test_defaults(self) -> None:
        req = ExecutionRequest(task_id="t1")
        assert req.task_id == "t1"
        assert req.max_tokens == 4096
        assert req.temperature == 0.7


class TestExecutionResult:
    def test_defaults(self) -> None:
        result = ExecutionResult(task_id="t1")
        assert not result.success
        assert result.output == ""


class TestArtifactReference:
    def test_default_content_type(self) -> None:
        ref = ArtifactReference(artifact_id="a1")
        assert ref.content_type == "application/octet-stream"


class TestSession:
    def test_default_state(self) -> None:
        session = Session(session_id="s1")
        assert session.state == SessionState.ACTIVE


class TestTaskRecord:
    def test_default_status(self) -> None:
        record = TaskRecord(task_id="t1")
        assert record.status == "pending"


class TestPrompt:
    def test_defaults(self) -> None:
        prompt = Prompt()
        assert prompt.goal == ""
        assert prompt.constraints == []


class TestContextBundle:
    def test_defaults(self) -> None:
        bundle = ContextBundle()
        assert bundle.immutable_core == ""
        assert bundle.working_set == []


class TestRoutingDecision:
    def test_defaults(self) -> None:
        decision = RoutingDecision()
        assert decision.selected_provider_id == ""
        assert decision.required_capabilities == []


class TestRoutingCandidate:
    def test_defaults(self) -> None:
        candidate = RoutingCandidate(provider_id="p1", agent_id="a1")
        assert candidate.provider_id == "p1"
        assert candidate.agent_id == "a1"
        assert candidate.score == 0.0


class TestPlan:
    def test_defaults(self) -> None:
        plan = Plan()
        assert plan.goal == ""
        assert plan.steps == []


class TestBudgetAllocation:
    def test_defaults(self) -> None:
        alloc = BudgetAllocation(layer_name="test")
        assert alloc.layer_name == "test"
        assert alloc.compression_ratio == 1.0


class TestCostEstimate:
    def test_defaults(self) -> None:
        estimate = CostEstimate(provider_id="p1")
        assert estimate.provider_id == "p1"
        assert estimate.currency == "credits"
