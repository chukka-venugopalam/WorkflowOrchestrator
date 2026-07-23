"""Unit tests for the StateEngine (state machine with append-only transition log)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from workflow_orchestrator.core.state_engine import (
    StateEngine,
    FileSystemStateStore,
    TransitionRecord,
    RunSnapshot,
    HeartbeatRecord,
)


class TestFileSystemStateStore:
    """Test suite for FileSystemStateStore."""

    def setup_method(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.store = FileSystemStateStore(self.temp_dir)

    def teardown_method(self) -> None:
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_append_and_get_transitions(self) -> None:
        """Test appending and retrieving transitions."""
        t1 = TransitionRecord(
            transition_id="t1",
            run_id="run1",
            from_status="",
            to_status="pending",
            data={"key": "value"},
        )
        t2 = TransitionRecord(
            transition_id="t2",
            run_id="run1",
            from_status="pending",
            to_status="running",
        )

        self.store.append_transition(t1)
        self.store.append_transition(t2)

        transitions = self.store.get_transitions("run1")
        assert len(transitions) == 2
        assert transitions[0].to_status == "pending"
        assert transitions[1].to_status == "running"

    def test_save_and_load_snapshot(self) -> None:
        """Test saving and loading a snapshot."""
        snapshot = RunSnapshot(
            run_id="run1",
            workflow_name="Test Workflow",
            status="running",
            current_step=2,
        )
        self.store.save_snapshot(snapshot)

        loaded = self.store.load_snapshot("run1")
        assert loaded is not None
        assert loaded.run_id == "run1"
        assert loaded.workflow_name == "Test Workflow"
        assert loaded.status == "running"
        assert loaded.current_step == 2

    def test_load_missing_snapshot(self) -> None:
        """Test loading a non-existent snapshot."""
        assert self.store.load_snapshot("nonexistent") is None

    def test_save_and_get_heartbeat(self) -> None:
        """Test saving and retrieving a heartbeat."""
        hb = HeartbeatRecord(run_id="run1", step_index=3)
        self.store.save_heartbeat(hb)

        loaded = self.store.get_latest_heartbeat("run1")
        assert loaded is not None
        assert loaded.run_id == "run1"
        assert loaded.step_index == 3

    def test_list_runs(self) -> None:
        """Test listing runs."""
        assert self.store.list_runs() == []
        self.store.save_snapshot(RunSnapshot(run_id="run_a", workflow_name="A"))
        self.store.save_snapshot(RunSnapshot(run_id="run_b", workflow_name="B"))
        runs = self.store.list_runs()
        assert len(runs) == 2
        assert "run_a" in runs
        assert "run_b" in runs

    def test_delete_run(self) -> None:
        """Test deleting a run's state data."""
        self.store.save_snapshot(RunSnapshot(run_id="run1", workflow_name="Test"))
        assert len(self.store.list_runs()) == 1
        self.store.delete_run("run1")
        assert len(self.store.list_runs()) == 0


class TestStateEngine:
    """Test suite for StateEngine."""

    def setup_method(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.store = FileSystemStateStore(self.temp_dir)
        self.engine = StateEngine(store=self.store)

    def teardown_method(self) -> None:
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_run(self) -> None:
        """Test creating a new run."""
        snapshot = self.engine.create_run("Test Workflow")
        assert snapshot.workflow_name == "Test Workflow"
        assert snapshot.status == "pending"
        assert snapshot.transition_count >= 1
        assert snapshot.started_at != ""

    def test_create_run_with_explicit_id(self) -> None:
        """Test creating a run with an explicit ID."""
        snapshot = self.engine.create_run("Test", run_id="my-run-1")
        assert snapshot.run_id == "my-run-1"

    def test_create_duplicate_run_raises(self) -> None:
        """Test that creating a duplicate run raises."""
        self.engine.create_run("Test", run_id="dup")
        with pytest.raises(ValueError, match="already exists"):
            self.engine.create_run("Test", run_id="dup")

    def test_valid_transition(self) -> None:
        """Test a valid state transition."""
        snapshot = self.engine.create_run("Test")
        snapshot = self.engine.transition(snapshot.run_id, "running")
        assert snapshot.status == "running"

    def test_invalid_transition_raises(self) -> None:
        """Test that invalid transitions raise ValueError."""
        snapshot = self.engine.create_run("Test")
        # pending -> completed is not allowed
        with pytest.raises(ValueError, match="Illegal transition"):
            self.engine.transition(snapshot.run_id, "completed")

    def test_full_lifecycle(self) -> None:
        """Test a complete run lifecycle."""
        snapshot = self.engine.create_run("Lifecycle Test")

        snapshot = self.engine.transition(snapshot.run_id, "running")
        assert snapshot.status == "running"

        snapshot = self.engine.transition(snapshot.run_id, "completed")
        assert snapshot.status == "completed"
        assert snapshot.completed_at != ""

    def test_current_snapshot(self) -> None:
        """Test getting the current snapshot."""
        snapshot = self.engine.create_run("Test")
        current = self.engine.current_snapshot(snapshot.run_id)
        assert current is not None
        assert current.run_id == snapshot.run_id

    def test_history(self) -> None:
        """Test getting transition history."""
        snapshot = self.engine.create_run("Test")
        self.engine.transition(snapshot.run_id, "running")
        self.engine.transition(snapshot.run_id, "completed")

        history = self.engine.history(snapshot.run_id)
        assert len(history) == 3  # pending, running, completed
        assert history[0].to_status == "pending"
        assert history[1].to_status == "running"
        assert history[2].to_status == "completed"

    def test_rebuild_from_log(self) -> None:
        """Test rebuilding snapshot from the transition log."""
        snapshot = self.engine.create_run("Rebuild Test")
        self.engine.transition(snapshot.run_id, "running")
        self.engine.transition(snapshot.run_id, "completed")

        # Delete the persisted snapshot
        # Remove the persisted snapshot file to simulate crash recovery
        snapshot_path = self.temp_dir / snapshot.run_id / "snapshot.json"
        if snapshot_path.exists():
            snapshot_path.unlink()

        # Rebuild from log
        rebuilt = self.engine.rebuild_from_log(snapshot.run_id)
        assert rebuilt is not None
        assert rebuilt.status == "completed"
        assert rebuilt.transition_count == 3

    def test_rebuild_from_empty_log(self) -> None:
        """Test rebuilding from an empty log returns None."""
        result = self.engine.rebuild_from_log("nonexistent")
        assert result is None

    def test_heartbeat(self) -> None:
        """Test recording and checking heartbeats."""
        snapshot = self.engine.create_run("Test")
        self.engine.transition(snapshot.run_id, "running")
        self.engine.record_heartbeat(snapshot.run_id, step_index=1)

        assert self.engine.check_heartbeat(snapshot.run_id, timeout_seconds=60)

    def test_expired_heartbeat(self) -> None:
        """Test that expired heartbeats are detected."""
        snapshot = self.engine.create_run("Test")
        self.engine.transition(snapshot.run_id, "running")

        assert not self.engine.check_heartbeat(snapshot.run_id, timeout_seconds=0)

    def test_interrupted_runs(self) -> None:
        """Test detection of interrupted runs."""
        snapshot = self.engine.create_run("Test")
        self.engine.transition(snapshot.run_id, "running")

        # With no heartbeat, should be detected as interrupted
        interrupted = self.engine.interrupted_runs()
        assert snapshot.run_id in interrupted

    def test_transition_with_data(self) -> None:
        """Test transitions with associated data."""
        snapshot = self.engine.create_run("Test", data={"initial": True})
        snapshot = self.engine.transition(
            snapshot.run_id,
            "running",
            actor="user",
            data={"progress": 50},
        )
        assert snapshot.status == "running"
        assert "progress" in snapshot.data

    def test_terminated_transitions_rejected(self) -> None:
        """Test that transitions from terminal states are rejected."""
        snapshot = self.engine.create_run("Test")
        self.engine.transition(snapshot.run_id, "running")
        self.engine.transition(snapshot.run_id, "completed")

        with pytest.raises(ValueError, match="terminal state"):
            self.engine.transition(snapshot.run_id, "running")
