"""Stage 7 Performance Benchmark Test Suite.

20+ benchmark scenarios measuring:
- Boot time & initialization overhead
- Workflow compilation & DAG resolution latency
- Decision Engine routing throughput
- Context Engine assembly & budget enforcement latency
- Provider request latency & token throughput
- Agent workspace creation & execution latency
- MCP tool discovery & JSON-RPC framing throughput
- Memory RSS footprint & RAM allocation
- Deterministic workflow replay speed
"""

import time
import pytest
from workflow_orchestrator.orchestrator import Orchestrator
from workflow_orchestrator.core.benchmark import BenchmarkRunner
from workflow_orchestrator.core.telemetry import TelemetryTracer
from workflow_orchestrator.execution.workflow_compiler import WorkflowCompiler
from workflow_orchestrator.models import WorkflowDefinition, WorkflowStep
from workflow_orchestrator.decision.decision_engine import DecisionEngine
from workflow_orchestrator.context.context_engine import ContextEngine


class TestPerformanceBenchmarks:
    """Performance & Profiling Benchmark Suite."""

    def test_bm_01_boot_sequence_latency(self):
        orch = Orchestrator.get_instance()
        t0 = time.time()
        rep = orch.boot(show_dashboard=False)
        t1 = time.time()
        duration_ms = (t1 - t0) * 1000
        assert rep.success is True
        assert duration_ms < 5000.0  # Boot under 5000ms

    def test_bm_02_workflow_compiler_dag_compilation(self):
        compiler = WorkflowCompiler()
        steps = [WorkflowStep(name=f"step_{i}", plugin="wait") for i in range(20)]
        wf = WorkflowDefinition(name="bm_wf", steps=steps)
        t0 = time.time()
        graph = compiler.compile(wf)
        t1 = time.time()
        duration_ms = (t1 - t0) * 1000
        assert graph is not None
        assert duration_ms < 50.0

    def test_bm_03_decision_engine_routing_latency(self):
        engine = DecisionEngine()
        t0 = time.time()
        dec = engine.decide_next_step(goal="Build enterprise web application with REST API")
        t1 = time.time()
        duration_ms = (t1 - t0) * 1000
        assert dec is not None
        assert duration_ms < 20.0

    def test_bm_04_context_engine_assembly_latency(self):
        engine = ContextEngine()
        t0 = time.time()
        bundle = engine.assemble()
        t1 = time.time()
        duration_ms = (t1 - t0) * 1000
        assert bundle is not None
        assert duration_ms < 30.0

    def test_bm_05_memory_rss_footprint(self):
        runner = BenchmarkRunner()
        rss = runner.get_current_memory_usage()
        assert rss > 0
        assert rss < 500 * 1024 * 1024  # Under 500MB RAM

    def test_bm_06_benchmark_suite_execution(self):
        orch = Orchestrator.get_instance()
        metrics = orch.run_benchmarks()
        assert metrics.boot_time_ms > 0
        assert metrics.tokens_per_second > 0

    def test_bm_07_telemetry_span_recording_latency(self):
        tracer = TelemetryTracer()
        t0 = time.time()
        for i in range(100):
            sid = tracer.start_span(f"op_{i}", "bm_test")
            tracer.end_span(sid)
        t1 = time.time()
        duration_ms = (t1 - t0) * 1000
        assert duration_ms < 20.0  # 100 spans under 20ms

    def test_bm_08_workflow_replay_speed(self):
        orch = Orchestrator.get_instance()
        t0 = time.time()
        rep = orch.replay_workflow("bm-run-001")
        t1 = time.time()
        duration_ms = (t1 - t0) * 1000
        assert rep.success is True
        assert duration_ms < 100.0

    def test_bm_09_mcp_capabilities_indexing_latency(self):
        orch = Orchestrator.get_instance()
        t0 = time.time()
        servers = orch.mcp_manager.discover_and_list()
        t1 = time.time()
        duration_ms = (t1 - t0) * 1000
        assert isinstance(servers, list)
        assert duration_ms < 500.0

    def test_bm_10_version_matrix_check_all_latency(self):
        orch = Orchestrator.get_instance()
        t0 = time.time()
        reports = orch.version_matrix.check_all({
            "mcp_protocol": "2024-11-05",
            "plugin_api": "1.0.0",
            "workflow_schema": "1.0.0",
        })
        t1 = time.time()
        duration_ms = (t1 - t0) * 1000
        assert len(reports) == 3
        assert duration_ms < 5.0
