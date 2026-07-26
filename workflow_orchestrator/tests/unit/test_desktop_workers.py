"""Unit tests for DesktopWorker abstraction layer and worker registry.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from workflow_orchestrator.workers.desktop_worker import (
    DesktopWorker,
    WorkerState,
    SkillCapability,
    DesktopWorkerTaskResult,
)
from workflow_orchestrator.workers.worker_registry import DesktopWorkerRegistry
from workflow_orchestrator.workers.implementations import (
    ClaudeCodeDesktopWorker,
    CursorDesktopWorker,
    CopilotDesktopWorker,
    OpenCodeDesktopWorker,
    OllamaDesktopWorker,
    OptionalWebDesktopWorker,
)
from workflow_orchestrator.orchestrator.orchestrator import Orchestrator


class TestDesktopWorkerAbstraction:
    def test_desktop_worker_lifecycle_states(self):
        worker = DesktopWorker(worker_id="test_worker", name="Test Worker")
        assert worker.state == WorkerState.STOPPED
        assert worker.discover() is True

        assert worker.start() is True
        assert worker.state == WorkerState.IDLE

        assert worker.heartbeat() is True

        res = worker.execute({"prompt": "Hello World"})
        assert res.success is True
        assert "Hello World" in res.output_text

        assert worker.pause() is True
        assert worker.state == WorkerState.PAUSED

        assert worker.resume() is True
        assert worker.state in (WorkerState.BUSY, WorkerState.IDLE)

        assert worker.recover() is True
        assert worker.state == WorkerState.IDLE

        assert worker.stop() is True
        assert worker.state == WorkerState.STOPPED

    def test_desktop_worker_registry(self):
        registry = DesktopWorkerRegistry()
        w1 = ClaudeCodeDesktopWorker()
        w2 = CursorDesktopWorker()

        registry.register_worker(w1)
        registry.register_worker(w2)

        assert len(registry.list_workers()) == 2
        assert registry.get_worker("claude_code_desktop") is w1

        backend_workers = registry.find_workers_by_skill("backend_api")
        assert len(backend_workers) == 1
        assert backend_workers[0] is w1

        frontend_workers = registry.find_workers_by_skill("frontend_ui")
        assert len(frontend_workers) == 1
        assert frontend_workers[0] is w2

        assert registry.unregister_worker("claude_code_desktop") is True
        assert len(registry.list_workers()) == 1

    def test_concrete_desktop_workers(self):
        workers = [
            ClaudeCodeDesktopWorker(),
            CursorDesktopWorker(),
            CopilotDesktopWorker(),
            OpenCodeDesktopWorker(),
            OllamaDesktopWorker("codellama"),
            OptionalWebDesktopWorker("chatgpt"),
        ]

        for w in workers:
            assert w.worker_id != ""
            assert w.name != ""
            assert len(w.skills) > 0
            
            # Real discovery check
            is_installed = w.discover()
            if is_installed:
                assert w.start() is True
                res = w.execute({"prompt": "Test Prompt"})
                assert isinstance(res, DesktopWorkerTaskResult)
                assert w.stop() is True
            else:
                res = w.execute({"prompt": "Test Prompt"})
                assert isinstance(res, DesktopWorkerTaskResult)

    def test_orchestrator_worker_registry_integration(self):
        orch = Orchestrator.get_instance()
        assert orch.worker_registry is not None
        registered = orch.worker_registry.list_workers()
        assert len(registered) >= 5
        worker_ids = [w.worker_id for w in registered]
        assert "claude_code_desktop" in worker_ids
        assert "cursor_desktop" in worker_ids
