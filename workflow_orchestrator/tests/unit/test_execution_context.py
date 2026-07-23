"""Unit tests for ExecutionContext."""

from __future__ import annotations

from workflow_orchestrator.execution.execution_context import ExecutionContext


class TestExecutionContext:
    """Tests for the ExecutionContext dataclass."""

    def test_create_default(self) -> None:
        """Test creating a context with default values."""
        ctx = ExecutionContext.create(workflow_name="test")
        assert ctx.workflow_name == "test"
        assert ctx.execution_id != ""
        assert ctx.workflow_id != ""
        assert ctx.profile == "default"
        assert ctx.variables == {}
        assert ctx.environment == {}
        assert ctx.artifacts == []
        assert ctx.outputs == {}
        assert ctx.started_at != ""

    def test_create_with_explicit_values(self) -> None:
        """Test creating a context with explicit values."""
        ctx = ExecutionContext.create(
            workflow_name="build",
            workflow_id="wf-123",
            execution_id="exec-456",
            profile="production",
            variables={"key": "value"},
            environment={"PATH": "/usr/bin"},
        )
        assert ctx.workflow_name == "build"
        assert ctx.workflow_id == "wf-123"
        assert ctx.execution_id == "exec-456"
        assert ctx.profile == "production"
        assert ctx.variables == {"key": "value"}
        assert ctx.environment == {"PATH": "/usr/bin"}

    def test_set_and_get_variable(self) -> None:
        """Test setting and getting variables."""
        ctx = ExecutionContext.create()
        ctx.set_variable("name", "test")
        assert ctx.get_variable("name") == "test"
        assert ctx.get_variable("missing") is None
        assert ctx.get_variable("missing", "default") == "default"

    def test_record_and_get_output(self) -> None:
        """Test recording and retrieving step outputs."""
        ctx = ExecutionContext.create()
        ctx.record_output("step_1", {"result": "ok"})
        assert ctx.get_output("step_1") == {"result": "ok"}
        assert ctx.get_output("missing") is None

    def test_add_artifact(self) -> None:
        """Test adding artifacts."""
        ctx = ExecutionContext.create()
        ctx.add_artifact({"id": "art-1", "name": "output.txt"})
        ctx.add_artifact({"id": "art-2", "name": "report.md"})
        assert len(ctx.artifacts) == 2

    def test_to_dict_and_from_dict(self) -> None:
        """Test serialization round-trip."""
        original = ExecutionContext.create(
            workflow_name="test",
            workflow_id="wf-1",
            execution_id="exec-1",
            variables={"key": "val"},
        )
        data = original.to_dict()
        restored = ExecutionContext.from_dict(data)
        assert restored.workflow_name == original.workflow_name
        assert restored.workflow_id == original.workflow_id
        assert restored.execution_id == original.execution_id
        assert restored.variables == original.variables
        assert restored.started_at == original.started_at

    def test_to_dict_missing_fields(self) -> None:
        """Test from_dict with missing optional fields."""
        restored = ExecutionContext.from_dict({})
        assert restored.workflow_id == ""
        assert restored.execution_id == ""

    def test_outputs_immutable_preserved(self) -> None:
        """Test that recorded outputs are preserved in serialization."""
        ctx = ExecutionContext.create()
        ctx.record_output("step_1", {"status": "done"})
        data = ctx.to_dict()
        assert data["outputs"]["step_1"]["status"] == "done"
