"""Unit tests for Project Memory."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


class TestProjectMemory:
    """Tests for ProjectMemory."""

    @pytest.fixture
    def project_memory(self, tmp_path):
        """Create a project memory instance."""
        from workflow_orchestrator.runtime import ProjectMemory
        return ProjectMemory(project_dir=str(tmp_path / "test-project"))

    def test_initialize(self, project_memory):
        """Test initializing the .state directory."""
        project_memory.initialize()

        assert project_memory.state_dir.exists()
        assert (project_memory.state_dir / "artifacts").exists()
        assert (project_memory.state_dir / "history").exists()
        assert (project_memory.state_dir / "summaries").exists()
        assert (project_memory.state_dir / "contract").exists()
        assert (project_memory.state_dir / "context").exists()

    def test_exists(self, project_memory):
        """Test checking if .state exists."""
        assert project_memory.exists() is False
        project_memory.initialize()
        assert project_memory.exists() is True

    def test_save_and_load_session(self, project_memory):
        """Test saving and loading session data."""
        session_data = {"session_id": "test-123", "state": "active", "project": "test"}
        project_memory.save_session(session_data)

        loaded = project_memory.load_session()
        assert loaded is not None
        assert loaded["session_id"] == "test-123"
        assert loaded["state"] == "active"

    def test_save_and_load_providers(self, project_memory):
        """Test saving and loading provider config."""
        providers = [
            {"id": "anthropic.claude", "enabled": True},
            {"id": "openai.chatgpt", "enabled": False},
        ]
        project_memory.save_providers(providers)

        loaded = project_memory.load_providers()
        assert len(loaded) == 2
        assert loaded[0]["id"] == "anthropic.claude"

    def test_save_and_load_agents(self, project_memory):
        """Test saving and loading agent config."""
        agents = [{"id": "claude-code", "enabled": True}]
        project_memory.save_agents(agents)

        loaded = project_memory.load_agents()
        assert len(loaded) == 1
        assert loaded[0]["id"] == "claude-code"

    def test_save_and_load_timeline(self, project_memory):
        """Test saving and loading timeline."""
        entries = [
            {"step": 1, "action": "analyze", "status": "completed"},
            {"step": 2, "action": "execute", "status": "running"},
        ]
        project_memory.save_timeline(entries)

        loaded = project_memory.load_timeline()
        assert len(loaded) == 2

    def test_append_timeline_entry(self, project_memory):
        """Test appending to the timeline."""
        project_memory.append_timeline_entry({"step": 1, "action": "start"})
        project_memory.append_timeline_entry({"step": 2, "action": "finish"})

        entries = project_memory.load_timeline()
        assert len(entries) == 2

    def test_save_and_load_artifact_metadata(self, project_memory):
        """Test saving and loading artifact metadata."""
        data = {"hash": "abc123", "size": 100}
        project_memory.save_artifact_metadata("art-1", data)

        loaded = project_memory.load_artifact_metadata("art-1")
        assert loaded is not None
        assert loaded["hash"] == "abc123"

    def test_list_artifact_ids(self, project_memory):
        """Test listing artifact IDs."""
        project_memory.save_artifact_metadata("art-1", {"hash": "abc"})
        project_memory.save_artifact_metadata("art-2", {"hash": "def"})

        ids = project_memory.list_artifact_ids()
        assert len(ids) == 2

    def test_save_and_load_history(self, project_memory):
        """Test saving and loading execution history."""
        history = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi"}]
        project_memory.save_history("session-1", history)

        loaded = project_memory.load_history("session-1")
        assert len(loaded) == 2

    def test_save_and_load_summary(self, project_memory):
        """Test saving and loading a summary."""
        project_memory.save_summary("step-1", "Summary of step 1")
        project_memory.save_summary("step-2", "Summary of step 2")

        content = project_memory.load_summary("step-1")
        assert content == "Summary of step 1"

        summaries = project_memory.list_summaries()
        assert len(summaries) == 2

    def test_save_and_load_contract(self, project_memory):
        """Test saving and loading contract data."""
        contract = {"version": "1.0.0", "project": "test"}
        project_memory.save_contract(contract)

        loaded = project_memory.load_contract()
        assert loaded is not None
        assert loaded["version"] == "1.0.0"

    def test_save_and_load_context_snapshot(self, project_memory):
        """Test saving and loading context snapshots."""
        snapshot = {"tokens": 1000, "layers": ["contract", "state"]}
        project_memory.save_context_snapshot("snap-1", snapshot)

        loaded = project_memory.load_context_snapshot("snap-1")
        assert loaded is not None
        assert loaded["tokens"] == 1000

    def test_clear(self, project_memory):
        """Test clearing project memory."""
        project_memory.initialize()
        assert project_memory.exists() is True

        project_memory.clear()
        assert project_memory.exists() is False

    def test_multiple_sessions_overwrite(self, project_memory):
        """Test saving multiple sessions (last one wins)."""
        project_memory.save_session({"session_id": "session-1", "state": "active"})
        project_memory.save_session({"session_id": "session-2", "state": "completed"})

        loaded = project_memory.load_session()
        assert loaded is not None
        assert loaded["session_id"] == "session-2"
