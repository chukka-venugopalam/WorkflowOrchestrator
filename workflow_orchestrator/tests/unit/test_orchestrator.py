"""Unit tests for the Orchestration Layer (`workflow_orchestrator.orchestrator`)."""

from __future__ import annotations

import pytest
from pathlib import Path

from workflow_orchestrator.orchestrator import (
    Orchestrator,
    BootSequence,
    ProviderManager,
    TransportManager,
    AgentManager,
    MCPManager,
    AutoDiscovery,
    WorkflowDoctor,
    SetupWizard,
    ProjectFlowEngine,
    SelfHealingEngine,
)


class TestBootSequence:
    def test_boot_sequence_execution(self) -> None:
        boot = BootSequence()
        report = boot.execute(show_dashboard=False)
        assert report.success is True
        assert len(report.steps) == 14
        assert report.failed_steps == []


class TestProviderManager:
    def test_discover_and_load(self) -> None:
        pm = ProviderManager()
        providers = pm.discover_and_load()
        assert len(providers) >= 10
        provider_ids = [p.provider_id for p in providers]
        assert "claude" in provider_ids
        assert "chatgpt" in provider_ids
        assert "gemini" in provider_ids

    def test_enable_disable_provider(self) -> None:
        pm = ProviderManager()
        pm.disable_provider("claude")
        p = pm.get_provider("claude")
        assert p is not None
        assert p.enabled is False

        pm.enable_provider("claude")
        p2 = pm.get_provider("claude")
        assert p2 is not None
        assert p2.enabled is True


class TestTransportManager:
    @pytest.mark.asyncio
    async def test_discover_transports(self) -> None:
        tm = TransportManager()
        statuses = await tm.discover_transports()
        assert len(statuses) == 6
        names = [s.name for s in statuses]
        assert "rest_api" in names
        assert "cli" in names


class TestAgentManager:
    def test_discover_agents(self) -> None:
        am = AgentManager()
        agents = am.discover_agents()
        assert len(agents) >= 7
        agent_ids = [a.agent_id for a in agents]
        assert "claude_code" in agent_ids
        assert "cursor" in agent_ids


class TestMCPManager:
    def test_add_and_list_mcp_servers(self) -> None:
        mcp = MCPManager()
        mcp.add_server("test_server", "node", ["index.js"])
        servers = mcp.discover_and_list()
        server_names = [s.name for s in servers]
        assert "test_server" in server_names


class TestAutoDiscovery:
    def test_full_discovery(self) -> None:
        ad = AutoDiscovery()
        audit = ad.run_full_discovery()
        assert audit.os_name != ""
        assert audit.python_version != ""


class TestWorkflowDoctor:
    def test_diagnose(self) -> None:
        doc = WorkflowDoctor()
        rep = doc.diagnose()
        assert rep.passed_count > 0
        assert len(rep.items) >= 8


class TestSetupWizard:
    def test_automated_setup(self) -> None:
        wiz = SetupWizard()
        cfg = wiz.run_automated_setup()
        assert cfg.workspace_path != ""


class TestProjectFlowEngine:
    def test_execute_project_from_prompt(self, tmp_path: Path) -> None:
        pfe = ProjectFlowEngine()
        rec = pfe.execute_project_from_prompt(
            idea="I want to build an AI tourism platform.",
            project_name="tourism_ai",
            workspace_dir=tmp_path,
        )
        assert rec.status == "completed"
        assert rec.project_name == "tourism_ai"


class TestSelfHealingEngine:
    def test_create_debug_package_and_repair(self) -> None:
        she = SelfHealingEngine()
        err = RuntimeError("Test execution crash")
        pkg = she.create_debug_package(err, "step_test")
        assert pkg.error_message == "Test execution crash"

        res = she.attempt_repair(pkg)
        assert res.success is True
        assert res.repaired_by != ""


class TestOrchestratorFacade:
    def test_orchestrator_boot_and_doctor(self) -> None:
        orch = Orchestrator.get_instance()
        boot_report = orch.boot(show_dashboard=False)
        assert boot_report.success is True

        diag = orch.run_doctor()
        assert diag.passed_count > 0
