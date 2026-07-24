"""Unit tests for Phase 6 production components:

- OpenRouterProvider, OllamaProvider, AzureOpenAIProvider
- OpenCodeAgent, FreeBuffAgent, AntigravityAgent
- McpProtocolClient & MCP Runtime
- ApprovalGateEngine & EncryptedCredentialVault
- PluginEngine & VersionMatrix
- BenchmarkRunner & TelemetryTracer
- WorkflowEngine replay_workflow
"""

import os
from pathlib import Path
import pytest

from workflow_orchestrator.providers.implementations import (
    OpenRouterProvider,
    OllamaProvider,
    AzureOpenAIProvider,
)
from workflow_orchestrator.agents.implementations import (
    OpenCodeAgent,
    FreeBuffAgent,
    AntigravityAgent,
)
from workflow_orchestrator.runtime.mcp_runtime import McpProtocolClient
from workflow_orchestrator.core.security import (
    ApprovalGateEngine,
    EncryptedCredentialVault,
    SecretRedactor,
    CommandSandbox,
    ActionRiskLevel,
)
from workflow_orchestrator.core.plugin_engine import PluginEngine
from workflow_orchestrator.core.version_matrix import VersionMatrix
from workflow_orchestrator.core.benchmark import BenchmarkRunner
from workflow_orchestrator.core.telemetry import TelemetryTracer
from workflow_orchestrator.intelligence.models import ExecutionRequest
from workflow_orchestrator.engine import WorkflowEngine


class TestPhase6Providers:
    @pytest.mark.asyncio
    async def test_openrouter_provider_manifest_and_simulation(self):
        p = OpenRouterProvider()
        await p.initialize()
        assert p.simulation_mode is True
        manifest = p.manifest()
        assert manifest.id == "openrouter"
        req = ExecutionRequest(goal="Generate python function")
        res = await p.execute(req)
        assert res.success is True
        assert "SIMULATION_MODE" in res.output

    @pytest.mark.asyncio
    async def test_ollama_provider_manifest_and_execution(self):
        p = OllamaProvider()
        await p.initialize()
        manifest = p.manifest()
        assert manifest.id == "ollama"
        req = ExecutionRequest(goal="Analyze log file")
        res = await p.execute(req)
        assert res.success is True

    @pytest.mark.asyncio
    async def test_azure_openai_provider_manifest(self):
        p = AzureOpenAIProvider()
        await p.initialize()
        manifest = p.manifest()
        assert manifest.id == "azure_openai"
        req = ExecutionRequest(goal="Summarize doc")
        res = await p.execute(req)
        assert res.success is True


class TestPhase6Agents:
    @pytest.mark.asyncio
    async def test_opencode_agent_manifest_and_simulation(self):
        agent = OpenCodeAgent()
        await agent.launch()
        manifest = agent.manifest()
        assert manifest.id == "opencode"
        req = ExecutionRequest(goal="Refactor project")
        res = await agent.execute(req)
        assert res.success is True

    @pytest.mark.asyncio
    async def test_freebuff_agent_manifest(self):
        agent = FreeBuffAgent()
        await agent.launch()
        manifest = agent.manifest()
        assert manifest.id == "freebuff"
        req = ExecutionRequest(goal="Clean code")
        res = await agent.execute(req)
        assert res.success is True

    @pytest.mark.asyncio
    async def test_antigravity_agent_manifest(self):
        agent = AntigravityAgent()
        await agent.launch()
        manifest = agent.manifest()
        assert manifest.id == "antigravity"
        req = ExecutionRequest(goal="Architecture review")
        res = await agent.execute(req)
        assert res.success is True


class TestSecurityEngine:
    def test_approval_gate_auto_approve_low_risk(self):
        gate = ApprovalGateEngine(interactive=False, auto_approve_low_risk=True)
        assert gate.check_approval("read_file", "test.py", ActionRiskLevel.LOW) is True

    def test_approval_gate_reject_destructive_non_interactive(self):
        gate = ApprovalGateEngine(interactive=False)
        assert gate.check_approval("delete_file", "test.py", ActionRiskLevel.HIGH) is False

    def test_encrypted_credential_vault(self):
        vault = EncryptedCredentialVault(master_key="secret-key")
        vault.set_secret("OPENAI_KEY", "sk-proj-1234567890")
        assert vault.get_secret("OPENAI_KEY") == "sk-proj-1234567890"

    def test_secret_redactor(self):
        log_text = "Connecting with API key sk-1234567890abcdef123456"
        redacted = SecretRedactor.redact(log_text)
        assert "[REDACTED_SECRET]" in redacted
        assert "sk-1234567890abcdef123456" not in redacted

    def test_command_sandbox(self):
        ws = Path.cwd()
        assert CommandSandbox.is_safe_path(ws / "sub" / "file.txt", ws) is True
        assert CommandSandbox.is_safe_path(ws.parent.parent, ws) is False


class TestPluginAndVersionMatrix:
    def test_plugin_engine_discovery(self):
        engine = PluginEngine()
        plugins = engine.discover_and_load()
        assert isinstance(plugins, list)

    def test_version_matrix_validation(self):
        report = VersionMatrix.validate_compatibility("mcp_protocol", "2024-11-05")
        assert report.compatible is True
        bad_report = VersionMatrix.validate_compatibility("mcp_protocol", "9.9.9")
        assert bad_report.compatible is False


class TestBenchmarkAndTelemetry:
    def test_benchmark_runner(self):
        bm = BenchmarkRunner()
        metrics = bm.run_benchmark_suite()
        assert metrics.boot_time_ms > 0
        assert metrics.memory_rss_bytes > 0

    def test_telemetry_tracer(self):
        tracer = TelemetryTracer()
        sid = tracer.start_span("test_op", "unit_test")
        tracer.end_span(sid)
        assert len(tracer.completed_spans) == 1
        graph = tracer.generate_dependency_graph()
        assert "MasterOrchestrator" in graph


class TestWorkflowReplay:
    def test_replay_workflow(self):
        engine = WorkflowEngine()
        report = engine.replay_workflow("run-1001")
        assert report.success is True
        assert report.metadata.get("replayed_from_run_id") == "run-1001"
