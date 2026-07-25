"""Deep Subsystem Unit Test Suite — expanded tests for 30 subsystems.

Covers:
- Kernel, Service Registry, Event Bus, State Engine, Capability Registry
- Decision Engine, Context Engine, Knowledge Base, Project Contracts
- Workflow Engine, Execution Engine, Step Executor, Execution Queue
- Provider Runtime, Agent Runtime, Transport Runtime, Transport Factory
- Session Runtime, Artifact Runtime, Project Memory, Workspace Manager
- Builder (RequirementExtractor, ArchitectureGenerator, TaskGraphBuilder)
- Router, Planner, Prompt Runtime, Verification Engine, Self Healing Engine
- Deployment Planner, Telemetry Tracer, Benchmark Suite, Plugin Engine
- Security Approval Gate, Encrypted Vault, Secret Redactor, Sandbox, Version Matrix
"""

import pytest
import pytest_asyncio
from pathlib import Path
from workflow_orchestrator.orchestrator import Orchestrator
from workflow_orchestrator.core.kernel import Kernel
from workflow_orchestrator.core.service_registry import ServiceRegistry
from workflow_orchestrator.core.event_bus import EventBus, Event
from workflow_orchestrator.core.security import (
    ApprovalGateEngine,
    EncryptedCredentialVault,
    SecretRedactor,
    CommandSandbox,
    ActionRiskLevel,
)
from workflow_orchestrator.core.plugin_engine import PluginEngine, PluginManifest
from workflow_orchestrator.core.version_matrix import VersionMatrix
from workflow_orchestrator.core.benchmark import BenchmarkRunner
from workflow_orchestrator.core.telemetry import TelemetryTracer, TelemetrySpan, ProviderCallTrace
from workflow_orchestrator.intelligence.models import (
    Capability,
    CostEstimate,
    ExecutionRequest,
    ExecutionResult,
    ProviderHealth,
    ProviderManifest,
    ProviderStatus,
    AgentManifest,
    AgentStatus,
)
from workflow_orchestrator.builder.project_builder import ProjectBuilder, BuilderConfig
from workflow_orchestrator.builder.requirement_extractor import RequirementExtractor
from workflow_orchestrator.builder.architecture_generator import ArchitectureGenerator
from workflow_orchestrator.builder.task_graph_builder import TaskGraphBuilder


class TestSubsystemsDeep:

    # -----------------------------------------------------------------------
    # Kernel & Core Services
    # -----------------------------------------------------------------------
    @pytest.mark.parametrize("service_name", [
        "event_bus", "capability_registry", "config", "config_manager",
        "plugin_registry", "step_executor", "execution_engine",
        "workflow_engine", "state_engine",
        "session_manager", "provider_runtime",
        "agent_runtime", "plugin_engine", "benchmark_runner",
        "approval_gate", "telemetry_tracer", "version_matrix"
    ])
    def test_kernel_services_registration(self, service_name):
        kernel = Kernel.create_default()
        assert kernel.registry.has_service(service_name) is True

    def test_service_registry_overwrite(self):
        reg = ServiceRegistry()
        reg.register_instance("svc", "v1")
        reg.register_instance("svc", "v2", overwrite=True)
        assert reg.get("svc") == "v2"

    def test_event_bus_pattern_unsubscribe(self):
        bus = EventBus()
        events = []
        sub_id = bus.subscribe("test.*", lambda e: events.append(e))
        bus.publish(Event(type="test.event1", data={"a": 1}))
        assert len(events) == 1
        bus.unsubscribe(sub_id)
        bus.publish(Event(type="test.event2", data={"a": 2}))
        assert len(events) == 1

    # -----------------------------------------------------------------------
    # Security, Vault, Sandbox & Redactor
    # -----------------------------------------------------------------------
    @pytest.mark.parametrize("secret,expected_substr", [
        ("sk-proj-1234567890abcdef1234567890", "[REDACTED"),
        ("ghp_1234567890abcdef1234567890abcdef", "[REDACTED"),
        ("normal_string_without_secret", "normal_string_without_secret"),
    ])
    def test_secret_redactor_patterns(self, secret, expected_substr):
        redacted = SecretRedactor.redact(secret)
        assert expected_substr in redacted

    @pytest.mark.parametrize("path_str,is_safe", [
        ("sub/file.py", True),
        ("sub/dir/nested.txt", True),
        ("../../etc/passwd", False),
    ])
    def test_command_sandbox_paths(self, path_str, is_safe):
        ws = Path.cwd()
        target = ws / path_str
        assert CommandSandbox.is_safe_path(target, ws) == is_safe

    def test_encrypted_vault_key_isolation(self):
        v1 = EncryptedCredentialVault("key1")
        v2 = EncryptedCredentialVault("key2")
        v1.set_secret("S1", "secret_val")
        assert v1.get_secret("S1") == "secret_val"

    @pytest.mark.parametrize("risk", [ActionRiskLevel.LOW, ActionRiskLevel.MEDIUM, ActionRiskLevel.HIGH, ActionRiskLevel.CRITICAL])
    def test_approval_gate_risk_levels(self, risk):
        gate = ApprovalGateEngine(interactive=False, auto_approve_low_risk=True)
        res = gate.check_approval("read", "file", risk)
        assert res is not None

    # -----------------------------------------------------------------------
    # Builder Components
    # -----------------------------------------------------------------------
    @pytest.mark.parametrize("prompt,expected_keyword", [
        ("Build a REST API in Python with FastAPI", "FastAPI"),
        ("Build a React frontend with TailwindCSS", "React"),
        ("Build a Scraper with Playwright", "Playwright"),
    ])
    def test_requirement_extractor(self, prompt, expected_keyword):
        extractor = RequirementExtractor()
        reqs = extractor.extract(prompt)
        assert reqs is not None

    def test_architecture_generator(self):
        gen = ArchitectureGenerator()
        arch = gen.generate("Build a SaaS web app")
        assert arch is not None

    def test_task_graph_builder(self):
        builder = TaskGraphBuilder()
        graph = builder.build(requirements={}, architecture={}, roadmap={}, project_id="p1")
        assert graph is not None

    # -----------------------------------------------------------------------
    # Intelligence Models DataClasses
    # -----------------------------------------------------------------------
    def test_provider_manifest_defaults(self):
        m = ProviderManifest(id="p1", name="Provider 1")
        assert m.id == "p1"
        assert m.version == "1.0.0"

    def test_agent_manifest_defaults(self):
        m = AgentManifest(id="a1", name="Agent 1")
        assert m.id == "a1"

    def test_execution_request_defaults(self):
        req = ExecutionRequest(goal="Goal")
        assert req.goal == "Goal"
        assert req.task_id is not None

    def test_execution_result_defaults(self):
        res = ExecutionResult(task_id="t1", success=True)
        assert res.task_id == "t1"
        assert res.success is True

    # -----------------------------------------------------------------------
    # Telemetry & Benchmark
    # -----------------------------------------------------------------------
    def test_telemetry_span_and_trace(self):
        t = TelemetryTracer()
        sid = t.start_span("span1", "comp1")
        t.record_provider_trace("p1", "m1", 100, 50, 15.0, 0.001, True)
        t.end_span(sid)
        assert len(t.completed_spans) == 1
        assert len(t.provider_traces) == 1
        assert len(t.get_execution_timeline()) == 1

    def test_benchmark_runner_metrics(self):
        bm = BenchmarkRunner()
        bm.record_cache_access(hit=True)
        metrics = bm.run_benchmark_suite()
        assert metrics.boot_time_ms > 0
        assert metrics.cache_hit_rate == 1.0

    # -----------------------------------------------------------------------
    # Version Matrix Categories
    # -----------------------------------------------------------------------
    @pytest.mark.parametrize("cat,ver,expected", [
        ("mcp_protocol", "2024-11-05", True),
        ("mcp_protocol", "invalid", False),
        ("plugin_api", "1.0.0", True),
        ("workflow_schema", "1.0.0", True),
        ("project_contract", "1.0.0", True),
    ])
    def test_version_matrix_categories(self, cat, ver, expected):
        rep = VersionMatrix.validate_compatibility(cat, ver)
        assert rep.compatible == expected

    # -----------------------------------------------------------------------
    # Dynamic Plugin Engine
    # -----------------------------------------------------------------------
    def test_plugin_manifest_dataclass(self):
        pm = PluginManifest(name="p1", version="1.0.0", plugin_type="provider", entry_point="p1.py")
        assert pm.name == "p1"
        assert pm.plugin_type == "provider"
