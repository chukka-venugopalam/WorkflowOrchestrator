"""Unit tests for the Orchestration Layer (`workflow_orchestrator.orchestrator`)."""

from __future__ import annotations

import pytest
from pathlib import Path

from workflow_orchestrator.orchestrator import (
    Orchestrator,
    BootSequence,
    ProviderManager,
    TransportManager,
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
        assert len(report.steps) == 15
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

    def test_invoke_provider_unavailable_raises_without_calling_execute(self, monkeypatch) -> None:
        pm = ProviderManager()
        pm.disable_provider("claude")
        called = False

        async def mock_exec(*args, **kwargs):
            nonlocal called
            called = True
            return None

        monkeypatch.setattr(pm.runtime, "execute", mock_exec)
        with pytest.raises(RuntimeError, match="not available or enabled"):
            pm.invoke_provider("claude", "Refine prompt")

        assert called is False

    def test_invoke_provider_unavailable_raises_without_calling_execute(self, monkeypatch) -> None:
        from workflow_orchestrator.integrations.provider_detector import DetectedProvider
        pm = ProviderManager()

        def mock_detect():
            return [DetectedProvider(provider_id="claude", name="Claude", available=False, unavailable_reason="Not installed")]

        monkeypatch.setattr(pm.detector, "detect_all", mock_detect)
        with pytest.raises(RuntimeError, match="not available"):
            pm.invoke_provider("claude", "Refine prompt")

    def test_invoke_provider_desktop_capture_success_returns_output(self, monkeypatch) -> None:
        from workflow_orchestrator.integrations.provider_detector import DetectedProvider
        pm = ProviderManager()

        def mock_detect():
            return [DetectedProvider(provider_id="anthropic.claude", name="Claude", available=True, transport="desktop", path="claude.exe")]

        monkeypatch.setattr(pm.detector, "detect_all", mock_detect)

        class SuccessUITransport:
            def __init__(self, target_window_title: str):
                pass
            def capture_response(self, prompt: str, timeout_seconds: float = 60.0) -> tuple[str, dict[str, str]]:
                return "web standard", {"capture_method": "accessibility_tree"}

        monkeypatch.setattr("workflow_orchestrator.integrations.transports.desktop_ui_transport.DesktopUITransport", SuccessUITransport)
        res = pm.invoke_provider("anthropic.claude", "Refine prompt")
        assert res == "web standard"

    def test_invoke_provider_desktop_capture_failure_raises(self, monkeypatch) -> None:
        from workflow_orchestrator.integrations.provider_detector import DetectedProvider
        pm = ProviderManager()

        def mock_detect():
            return [DetectedProvider(provider_id="anthropic.claude", name="Claude", available=True, transport="desktop", path="claude.exe")]

        monkeypatch.setattr(pm.detector, "detect_all", mock_detect)

        class FailingUITransport:
            def __init__(self, target_window_title: str):
                pass
            def capture_response(self, prompt: str, timeout_seconds: float = 60.0) -> tuple[str, dict[str, str]]:
                raise RuntimeError("Failed to capture response from desktop GUI app via accessibility_tree, clipboard, or OCR")

        monkeypatch.setattr("workflow_orchestrator.integrations.transports.desktop_ui_transport.DesktopUITransport", FailingUITransport)
        with pytest.raises(RuntimeError, match="accessibility_tree"):
            pm.invoke_provider("anthropic.claude", "Refine prompt")

    def test_project_classifier_excludes_coding_agents_from_disambiguation(self, monkeypatch) -> None:
        from workflow_orchestrator.builder.project_classifier import ProjectClassifier, ProjectType
        from workflow_orchestrator.integrations.provider_detector import DetectedProvider
        pc = ProjectClassifier()
        pm = ProviderManager()

        # Provide both coding agent and conversational providers
        def mock_detect():
            return [
                DetectedProvider(provider_id="opencode", name="OpenCode", available=True, transport="cli", path="opencode"),
                DetectedProvider(provider_id="freebuff", name="FreeBuff", available=True, transport="cli", path="freebuff"),
                DetectedProvider(provider_id="antigravity", name="Antigravity", available=True, transport="desktop", path="antigravity"),
            ]

        monkeypatch.setattr(pm.detector, "detect_all", mock_detect)

        attempted_providers = []
        def spy_invoke(provider_id, prompt):
            attempted_providers.append(provider_id)
            raise RuntimeError("Failed")

        monkeypatch.setattr(pm, "invoke_provider", spy_invoke)

        res_type, res_scale = pc.classify_with_disambiguation(
            description="a system that could be web or desktop or cli",
            project_name="test_filter",
            provider_manager=pm,
            prompt_user_fn=lambda d, s: "cli minimal",
        )

        # Assert opencode, freebuff, and antigravity were NEVER attempted for disambiguation
        assert "opencode" not in attempted_providers
        assert "freebuff" not in attempted_providers
        assert "antigravity" not in attempted_providers
        assert res_type == ProjectType.CLI


class TestTransportManager:
    @pytest.mark.asyncio
    async def test_discover_transports(self) -> None:
        tm = TransportManager()
        statuses = await tm.discover_transports()
        assert len(statuses) == 6
        names = [s.name for s in statuses]
        assert "rest_api" in names
        assert "cli" in names


class TestWorkerRegistry:
    def test_discover_workers(self) -> None:
        from workflow_orchestrator.workers.worker_registry import DesktopWorkerRegistry
        from workflow_orchestrator.workers.implementations import CursorDesktopWorker, AntigravityDesktopWorker
        wr = DesktopWorkerRegistry()
        wr.register_worker(CursorDesktopWorker())
        wr.register_worker(AntigravityDesktopWorker())
        wr.discover_and_start_all()
        workers = wr.list_workers()
        assert len(workers) >= 2
        worker_ids = [w.worker_id for w in workers]
        assert "cursor_desktop" in worker_ids
        assert "antigravity_desktop" in worker_ids


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
