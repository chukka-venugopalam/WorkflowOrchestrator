"""Unit tests for Context Engine sub-components."""

from __future__ import annotations

from workflow_orchestrator.context.context_budget import ContextBudget
from workflow_orchestrator.context.context_builder import ContextBuilder
from workflow_orchestrator.context.context_cache import ContextCache
from workflow_orchestrator.context.context_compressor import ContextCompressor
from workflow_orchestrator.context.context_index import ContextIndex
from workflow_orchestrator.context.context_layers import ContextLayers
from workflow_orchestrator.context.context_models import (
    BudgetPriority,
    ContextAssembly,
    ContextLayer,
    ContextLayerContent,
)
from workflow_orchestrator.context.context_selector import ContextSelector
from workflow_orchestrator.context.context_snapshot import ContextSnapshotManager


class TestContextLayers:
    """Tests for ContextLayers."""

    def test_contract_layer(self) -> None:
        layer = ContextLayers.contract("Test contract")
        assert layer.layer == ContextLayer.PROJECT_CONTRACT
        assert layer.priority == BudgetPriority.CRITICAL

    def test_workflow_state_layer(self) -> None:
        layer = ContextLayers.workflow_state({"status": "running"})
        assert layer.layer == ContextLayer.WORKFLOW_STATE

    def test_artifacts_layer(self) -> None:
        layer = ContextLayers.artifacts("Build output")
        assert layer.layer == ContextLayer.RELEVANT_ARTIFACTS

    def test_history_layer(self) -> None:
        layer = ContextLayers.history("Executed step_1")
        assert layer.layer == ContextLayer.EXECUTION_HISTORY

    def test_knowledge_layer(self) -> None:
        layer = ContextLayers.knowledge("Python best practices")
        assert layer.layer == ContextLayer.RELEVANT_KNOWLEDGE

    def test_preferences_layer(self) -> None:
        layer = ContextLayers.preferences("prefer fast mode")
        assert layer.layer == ContextLayer.USER_PREFERENCES

    def test_errors_layer(self) -> None:
        layer = ContextLayers.errors("Connection timeout")
        assert layer.layer == ContextLayer.RECENT_ERRORS

    def test_summary_layer(self) -> None:
        layer = ContextLayers.summary("Completed coding phase")
        assert layer.layer == ContextLayer.ROLLING_SUMMARY

    def test_layer_order(self) -> None:
        order = ContextLayers.layer_order()
        assert order[0] == ContextLayer.PROJECT_CONTRACT
        assert order[-1] == ContextLayer.ROLLING_SUMMARY

    def test_estimate_tokens(self) -> None:
        tokens = ContextLayers.estimate_tokens("hello world")
        assert tokens > 0


class TestContextBudget:
    """Tests for ContextBudget."""

    def setup_method(self) -> None:
        self.budget = ContextBudget(total_budget=8000)

    def test_allocate_critical_first(self) -> None:
        layers = [
            ContextLayers.contract("x" * 2000),
            ContextLayers.history("x" * 2000),
        ]
        allocation = self.budget.allocate(layers)
        assert ContextLayer.PROJECT_CONTRACT in allocation
        assert ContextLayer.EXECUTION_HISTORY in allocation

    def test_enforce_prunes_optional(self) -> None:
        assembly = ContextAssembly(
            layers=[
                ContextLayers.contract("Small contract"),
                ContextLayers.summary("Optional summary that will be pruned with tiny budget"),
            ],
            total_tokens=10000,
            budget_limit=100,
        )
        self.budget.total_budget = 100
        result = self.budget.enforce(assembly)
        assert result.total_tokens <= 200

    def test_remaining(self) -> None:
        assembly = ContextAssembly(layers=[ContextLayers.contract("Hello")], total_tokens=10)
        remaining = self.budget.remaining(assembly)
        assert remaining > 0

    def test_can_fit(self) -> None:
        assembly = ContextAssembly(layers=[], total_tokens=0)
        layer = ContextLayers.contract("Test")
        assert self.budget.can_fit(layer, assembly)


class TestContextCompressor:
    """Tests for ContextCompressor."""

    def setup_method(self) -> None:
        self.compressor = ContextCompressor()

    def test_truncate(self) -> None:
        result = self.compressor.compress("Hello world " * 1000, max_tokens=100)
        assert result.compressed_tokens <= 100

    def test_no_compression_needed(self) -> None:
        result = self.compressor.compress("Short text", max_tokens=1000)
        assert result.compression_ratio == 0.0

    def test_sections(self) -> None:
        content = "SECTION 1\nContent here\n## Subsection\nMore content"
        result = self.compressor.compress(content, max_tokens=100, method="sections")
        assert result.compressed_content != ""


class TestContextIndex:
    """Tests for ContextIndex."""

    def setup_method(self) -> None:
        self.index = ContextIndex()

    def test_index_and_lookup(self) -> None:
        self.index.index("key1", ContextLayer.WORKFLOW_STATE, "test content")
        entry = self.index.lookup("key1")
        assert entry is not None
        assert entry.key == "key1"

    def test_lookup_not_found(self) -> None:
        assert self.index.lookup("nonexistent") is None

    def test_lookup_by_layer(self) -> None:
        self.index.index("k1", ContextLayer.WORKFLOW_STATE, "content")
        self.index.index("k2", ContextLayer.WORKFLOW_STATE, "more")
        entries = self.index.lookup_by_layer(ContextLayer.WORKFLOW_STATE)
        assert len(entries) == 2

    def test_search(self) -> None:
        self.index.index("key1", ContextLayer.WORKFLOW_STATE, "build output log")
        results = self.index.search("build")
        assert len(results) > 0

    def test_remove(self) -> None:
        self.index.index("key1", ContextLayer.WORKFLOW_STATE, "content")
        assert self.index.remove("key1")
        assert self.index.lookup("key1") is None

    def test_clear(self) -> None:
        self.index.index("key1", ContextLayer.WORKFLOW_STATE, "content")
        self.index.clear()
        assert self.index.count == 0


class TestContextCache:
    """Tests for ContextCache."""

    def setup_method(self) -> None:
        self.cache = ContextCache(max_size=10, ttl_seconds=300)

    def test_put_and_get(self) -> None:
        assembly = ContextAssembly(layers=[], total_tokens=100)
        key = self.cache.make_key({"test": "data"})
        self.cache.put(key, assembly)
        cached = self.cache.get(key)
        assert cached is not None
        assert cached.total_tokens == 100

    def test_miss(self) -> None:
        assert self.cache.get("nonexistent") is None

    def test_invalidate(self) -> None:
        assembly = ContextAssembly(layers=[], total_tokens=100)
        key = self.cache.make_key({"test": "data"})
        self.cache.put(key, assembly)
        assert self.cache.invalidate(key)
        assert self.cache.get(key) is None


class TestContextSnapshot:
    """Tests for ContextSnapshotManager."""

    def setup_method(self) -> None:
        self.mgr = ContextSnapshotManager()

    def test_create_and_load(self) -> None:
        assembly = ContextAssembly(layers=[], total_tokens=100)
        snapshot = self.mgr.create(assembly, workflow_id="wf-1", step_index=1)
        loaded = self.mgr.load(snapshot.snapshot_id)
        assert loaded is not None
        assert loaded.workflow_id == "wf-1"

    def test_find_by_workflow(self) -> None:
        assembly = ContextAssembly(layers=[], total_tokens=100)
        self.mgr.create(assembly, workflow_id="wf-1")
        snapshots = self.mgr.find_by_workflow("wf-1")
        assert len(snapshots) == 1

    def test_find_by_step(self) -> None:
        assembly = ContextAssembly(layers=[], total_tokens=100)
        self.mgr.create(assembly, workflow_id="wf-1", step_index=5)
        found = self.mgr.find_by_step("wf-1", 5)
        assert found is not None


class TestContextSelector:
    """Tests for ContextSelector."""

    def test_select_for_step(self) -> None:
        selector = ContextSelector()
        layers = selector.select_for_step("verify.build")
        assert len(layers) > 0

    def test_select_for_error(self) -> None:
        selector = ContextSelector()
        layers = selector.select_for_error("timeout", "Timed out")
        assert len(layers) > 0

    def test_select_for_phase_change(self) -> None:
        selector = ContextSelector()
        layers = selector.select_for_phase_change("deployment")
        assert len(layers) > 0
