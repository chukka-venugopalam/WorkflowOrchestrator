"""Unit tests for Context Engine."""

from __future__ import annotations

from workflow_orchestrator.context.context_engine import ContextEngine
from workflow_orchestrator.context.context_models import ContextLayer


class TestContextEngine:
    """Tests for the ContextEngine."""

    def setup_method(self) -> None:
        self.engine = ContextEngine()

    def test_assemble_empty(self) -> None:
        """Test assembling with no inputs."""
        assembly = self.engine.assemble()
        assert assembly.total_tokens >= 0
        assert assembly.assembly_id != ""

    def test_assemble_with_contract(self) -> None:
        """Test assembling with a contract."""
        assembly = self.engine.assemble(
            contract="Project: Test\nVision: Build something great",
        )
        layer_names = [l.layer.value for l in assembly.layers]
        assert "project_contract" in layer_names

    def test_assemble_with_state(self) -> None:
        """Test assembling with workflow state."""
        assembly = self.engine.assemble(
            state={"status": "running", "completed_steps": ["step_1"]},
        )
        assert assembly.total_tokens > 0

    def test_assemble_with_artifacts(self) -> None:
        """Test assembling with artifacts."""
        assembly = self.engine.assemble(
            artifacts=[{"name": "build.log", "summary": "Build succeeded"}],
        )
        assert assembly.total_tokens > 0

    def test_assemble_budget_limit(self) -> None:
        """Test that budget limit is respected."""
        large_content = "x" * 100000
        assembly = self.engine.assemble(
            contract=large_content,
            state={"key": "value"},
            budget_limit=1000,
        )
        assert assembly.total_tokens <= 2000  # Budget + some slack

    def test_snapshot_and_restore(self) -> None:
        """Test creating and restoring a snapshot."""
        assembly = self.engine.assemble(contract="Test contract")
        snapshot = self.engine.snapshot(assembly, workflow_id="wf-1", step_index=1)
        assert snapshot.snapshot_id != ""

        restored = self.engine.restore(snapshot.snapshot_id)
        assert restored is not None
        assert len(restored.layers) == len(assembly.layers)

    def test_to_bundle(self) -> None:
        """Test converting assembly to bundle."""
        assembly = self.engine.assemble(
            contract="Test contract",
            state={"status": "running"},
        )
        bundle = self.engine.to_bundle(assembly)
        assert "immutable_core" in bundle
        assert "total_tokens" in bundle
        assert "budget_remaining" in bundle

    def test_select_for_step(self) -> None:
        """Test selecting context for a step."""
        layers = self.engine.select_for_step("verify.build")
        assert isinstance(layers, list)

    def test_select_for_error(self) -> None:
        """Test selecting context for an error."""
        layers = self.engine.select_for_error("timeout", "Step timed out")
        assert len(layers) > 0

    def test_with_budget(self) -> None:
        """Test creating engine with different budget."""
        engine = self.engine.with_budget(500)
        assert engine.budget.total_budget == 500
