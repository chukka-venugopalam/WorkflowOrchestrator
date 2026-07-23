"""Unit tests for Artifact Runtime."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from workflow_orchestrator.core.artifact_manager import ArtifactManager, ArtifactRef


class TestArtifactRuntime:
    """Tests for Artifact Runtime."""

    @pytest.fixture
    def artifact_runtime(self, tmp_path):
        """Create an artifact runtime with temp storage."""
        from workflow_orchestrator.core.artifact_manager import ArtifactManager
        from workflow_orchestrator.runtime import ArtifactRuntime

        artifact_manager = ArtifactManager(base_path=str(tmp_path / "artifacts"))
        return ArtifactRuntime(artifact_manager=artifact_manager)

    def test_store_provider_output(self, artifact_runtime):
        """Test storing a provider's output as an artifact."""
        ref = artifact_runtime.store_provider_output(
            content=b"generated code",
            provider_id="anthropic.claude",
            agent_id="claude-code",
            session_id="session-123",
            origin_prompt="Generate a login page",
        )

        assert ref is not None
        assert ref.artifact_id is not None
        assert ref.hash is not None

        # Verify content is stored
        content = artifact_runtime.load(ref)
        assert content == b"generated code"

    def test_store_agent_output(self, artifact_runtime):
        """Test storing an agent's output as an artifact."""
        ref = artifact_runtime.store_agent_output(
            content=b"agent output",
            agent_id="claude-code",
            session_id="session-456",
        )

        assert ref is not None
        content = artifact_runtime.load(ref)
        assert content == b"agent output"

    def test_get_metadata(self, artifact_runtime):
        """Test getting artifact metadata."""
        ref = artifact_runtime.store_provider_output(
            content=b"test",
            provider_id="test-provider",
        )

        meta = artifact_runtime.get_metadata(ref.artifact_id)
        assert meta is not None
        assert meta.hash == ref.hash

    def test_get_provenance(self, artifact_runtime):
        """Test getting artifact provenance."""
        ref = artifact_runtime.store_provider_output(
            content=b"test",
            provider_id="test-provider",
            agent_id="test-agent",
            session_id="session-1",
            origin_prompt="Test prompt",
        )

        provenance = artifact_runtime.get_provenance(ref.artifact_id)
        assert provenance is not None
        assert provenance["provider_id"] == "test-provider"
        assert provenance["agent_id"] == "test-agent"
        assert provenance["session_id"] == "session-1"

    def test_artifact_dependencies(self, artifact_runtime):
        """Test tracking artifact dependencies."""
        parent = artifact_runtime.store_provider_output(
            content=b"parent",
            provider_id="provider1",
        )
        child = artifact_runtime.store_provider_output(
            content=b"child",
            provider_id="provider2",
            parent_ids=[parent.artifact_id],
        )

        deps = artifact_runtime.get_artifact_dependencies(child.artifact_id)
        assert len(deps) == 1
        assert deps[0] == parent.artifact_id

    def test_artifact_chain(self, artifact_runtime):
        """Test getting the full artifact ancestry chain."""
        a1 = artifact_runtime.store_provider_output(content=b"a1", provider_id="p1")
        a2 = artifact_runtime.store_provider_output(
            content=b"a2", provider_id="p2", parent_ids=[a1.artifact_id],
        )
        a3 = artifact_runtime.store_provider_output(
            content=b"a3", provider_id="p3", parent_ids=[a2.artifact_id],
        )

        chain = artifact_runtime.get_artifact_chain(a3.artifact_id)
        assert len(chain) == 3

    def test_verify_integrity(self, artifact_runtime):
        """Test verifying artifact integrity."""
        ref = artifact_runtime.store_provider_output(
            content=b"test content",
            provider_id="test",
        )

        assert artifact_runtime.verify_integrity(ref.artifact_id) is True
        assert artifact_runtime.verify_integrity("nonexistent") is False

    def test_list_by_session(self, artifact_runtime):
        """Test listing artifacts by session."""
        artifact_runtime.store_provider_output(
            content=b"test1",
            provider_id="p1",
            session_id="session-1",
        )
        artifact_runtime.store_provider_output(
            content=b"test2",
            provider_id="p2",
            session_id="session-1",
        )

        refs = artifact_runtime.list_by_session("session-1")
        assert len(refs) == 2


class TestArtifactManager:
    """Tests for ArtifactManager (core)."""

    @pytest.fixture
    def artifact_manager(self, tmp_path):
        """Create an artifact manager."""
        return ArtifactManager(base_path=str(tmp_path / "artifacts"))

    def test_store_and_load(self, artifact_manager):
        """Test storing and loading artifact content."""
        ref = artifact_manager.store(b"hello world", source="test")
        content = artifact_manager.load(ref)
        assert content == b"hello world"

    def test_store_deduplication(self, artifact_manager):
        """Test that duplicate content is not stored twice."""
        ref1 = artifact_manager.store(b"same content", source="test1")
        ref2 = artifact_manager.store(b"same content", source="test2")

        # Same hash
        assert ref1.hash == ref2.hash
        # Different artifact IDs
        assert ref1.artifact_id != ref2.artifact_id

    def test_store_file(self, artifact_manager, tmp_path):
        """Test storing a file as an artifact."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("file content")

        ref = artifact_manager.store_file(file_path, source="file_test")
        content = artifact_manager.load(ref)
        assert content == b"file content"

    def test_load_by_id(self, artifact_manager):
        """Test loading artifact by ID."""
        ref = artifact_manager.store(b"test", source="test")
        content = artifact_manager.load_by_id(ref.artifact_id)
        assert content == b"test"

    def test_get_ref(self, artifact_manager):
        """Test getting an ArtifactRef by ID."""
        ref = artifact_manager.store(b"test", source="test")
        retrieved = artifact_manager.get_ref(ref.artifact_id)
        assert retrieved is not None
        assert retrieved.hash == ref.hash

    def test_list_artifacts(self, artifact_manager):
        """Test listing artifacts."""
        artifact_manager.store(b"test1", source="test")
        artifact_manager.store(b"test2", source="test")

        artifacts = artifact_manager.list_artifacts()
        assert len(artifacts) == 2

    def test_verify_integrity(self, artifact_manager):
        """Test verifying artifact integrity."""
        ref = artifact_manager.store(b"test", source="test")
        assert artifact_manager.verify_integrity(ref) is True

    @staticmethod
    def test_compute_hash():
        """Test hash computation."""
        h = ArtifactManager.compute_hash(b"test")
        assert len(h) == 64  # SHA-256 hex digest
        assert isinstance(h, str)
