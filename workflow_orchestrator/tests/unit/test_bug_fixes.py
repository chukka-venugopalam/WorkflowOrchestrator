"""Unit tests for the 6 confirmed bug fixes in Workflow Orchestrator.
"""

from __future__ import annotations

import logging
import os
import pytest
from pathlib import Path

from workflow_orchestrator.integrations.provider_detector import ProviderDetector, DetectedProvider
from workflow_orchestrator.orchestrator.provider_manager import ProviderManager, ProviderMetadata
from workflow_orchestrator.core.logger import configure_logging
from workflow_orchestrator.execution.parallel_task_queue import ParallelTaskQueue, TaskProgressState
from workflow_orchestrator.builder.project_builder import ProjectBuilder


def test_bug1_provider_id_namespace_mapping():
    """Bug 1: Verify ProviderManager maps namespaced provider IDs to KNOWN_PROVIDERS."""
    mgr = ProviderManager()
    providers = mgr.discover_and_load()
    p_ids = [p.provider_id for p in providers]

    assert "claude" in p_ids
    assert "github_copilot" in p_ids
    assert "gemini" in p_ids
    assert "ollama" in p_ids
    assert "openrouter" in p_ids

    # Sanity check: Ensure ProviderDetector emitted IDs map to KNOWN_PROVIDERS
    detector = ProviderDetector()
    detected = detector.detect_all()
    for d in detected:
        matched = False
        for k in mgr.KNOWN_PROVIDERS:
            candidates = mgr.PROVIDER_ID_MAP.get(k, [k])
            if d.provider_id in candidates or d.provider_id.split(".")[-1] in candidates or d.provider_id == k:
                matched = True
                break
        assert matched, f"Detected provider_id '{d.provider_id}' has no matching entry in ProviderManager.KNOWN_PROVIDERS!"


def test_bug2_ollama_and_openrouter_detection():
    """Bug 2: Verify Ollama and OpenRouter detectors exist and return DetectedProvider."""
    detector = ProviderDetector()
    ollama_res = detector._detect_ollama()
    openrouter_res = detector._detect_openrouter()

    assert isinstance(ollama_res, DetectedProvider)
    assert ollama_res.provider_id == "ollama"

    assert isinstance(openrouter_res, DetectedProvider)
    assert openrouter_res.provider_id == "openrouter"


def test_bug3_unavailable_reason_propagation():
    """Bug 3: Verify unavailable_reason field propagates negative detection details."""
    detector = ProviderDetector()
    detected = detector.detect_all()

    for p in detected:
        if not p.available:
            assert p.unavailable_reason != "", f"Unavailable provider {p.name} missing unavailable_reason!"

    mgr = ProviderManager()
    providers = mgr.discover_and_load()
    for meta in providers:
        assert hasattr(meta, "unavailable_reason")
        if meta.status != "available" and not meta.api_key_configured:
            assert meta.unavailable_reason != "", f"ProviderMetadata {meta.name} missing unavailable_reason!"


def test_bug4_logging_initialization():
    """Bug 4: Verify configure_logging initializes root logger handlers cleanly."""
    configure_logging(level="INFO", log_to_file=False, log_to_console=True)
    root = logging.getLogger()
    assert len(root.handlers) >= 1


def test_bug5_pipeline_wall_clock_timeout():
    """Bug 5: Verify ParallelTaskQueue halts execution when max_total_seconds is exceeded."""
    queue = ParallelTaskQueue()
    queue.add_task("t1", "Timeout Task 1", "backend_api", "Do something 1")
    queue.add_task("t2", "Timeout Task 2", "frontend_ui", "Do something 2")

    # Pass max_total_seconds = -1.0 to force immediate timeout
    res = queue.execute_queue(max_total_seconds=-1.0)
    assert res["t1"] == TaskProgressState.FAILED
    assert "timeout" in queue.tasks["t1"].error_log.lower()


def test_bug6_project_builder_project_root_wiring():
    """Bug 6: Verify ProjectBuilder.build honors explicit project_root argument."""
    builder = ProjectBuilder()
    custom_root = Path.cwd() / "scratch" / "test_root_wiring"

    # Call build with project_root argument
    res = builder.build(idea="Test Root Wiring Project", project_name="test_root", project_root=custom_root)
    assert builder._config.builder.project_root == custom_root
    assert builder._initializer._config.project_root == custom_root
