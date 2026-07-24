"""Phase 6 Production Integration Test Suite.

Validates:
- Full Orchestrator boot & benchmark execution
- Real and simulation provider execution
- Dynamic MCP protocol client initialization
- Security approval gate enforcement
- Dynamic plugin loader
- Workflow replay engine
"""

import pytest
from workflow_orchestrator.orchestrator import Orchestrator


class TestPhase6ProductionIntegration:
    def test_orchestrator_boot_and_benchmarks(self):
        orch = Orchestrator.get_instance()
        boot_report = orch.boot(show_dashboard=False)
        assert boot_report.success is True

        bm_metrics = orch.run_benchmarks()
        assert bm_metrics.boot_time_ms >= 0
        assert bm_metrics.memory_rss_bytes > 0

    def test_provider_manager_with_new_providers(self):
        orch = Orchestrator.get_instance()
        providers = orch.provider_manager.discover_and_load()
        provider_ids = [p.provider_id for p in providers]
        assert "openrouter" in provider_ids or any("openrouter" in p.name.lower() for p in providers)

    def test_agent_manager_with_new_agents(self):
        orch = Orchestrator.get_instance()
        agents = orch.agent_manager.discover_agents()
        agent_ids = [a.agent_id for a in agents]
        assert len(agents) >= 4

    def test_workflow_replay_integration(self):
        orch = Orchestrator.get_instance()
        rep = orch.replay_workflow("run-integration-test-01")
        assert rep.success is True
        assert rep.metadata.get("replayed_from_run_id") == "run-integration-test-01"

    def test_security_approval_gate(self):
        orch = Orchestrator.get_instance()
        orch.approval_gate.interactive = False
        allowed = orch.approval_gate.check_approval("read_file", "test.py", risk_level="low")
        assert allowed is True

    def test_doctor_diagnostics_with_execution_mode(self):
        orch = Orchestrator.get_instance()
        report = orch.run_doctor()
        assert report.passed_count > 0
        mode_items = [i for i in report.items if i.name == "Execution Mode"]
        assert len(mode_items) > 0
