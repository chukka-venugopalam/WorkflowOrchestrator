"""Unit tests for the ArtifactManager."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from workflow_orchestrator.core.artifact_manager import (
    ArtifactManager,
    ArtifactRef,
    ArtifactMetadata,
)


class TestArtifactManager:
    """Test suite for ArtifactManager."""

    def setup_method(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = ArtifactManager(base_path=self.temp_dir / "artifacts")

    def teardown_method(self) -> None:
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_store_and_load(self) -> None:
        """Test storing and loading artifact content."""
        content = b"Hello, World!"
        ref = self.manager.store(content, source="test", tags=["example"])

        assert ref.hash != ""
        assert ref.path.exists()
        assert ref.metadata.size_bytes == len(content)

        loaded = self.manager.load(ref)
        assert loaded == content

    def test_store_file(self) -> None:
        """Test storing a file as an artifact."""
        file_path = self.temp_dir / "test.txt"
        file_path.write_bytes(b"file content")

        ref = self.manager.store_file(file_path, source="file test")
        loaded = self.manager.load(ref)
        assert loaded == b"file content"

    def test_store_file_not_found(self) -> None:
        """Test that storing a non-existent file raises."""
        with pytest.raises(FileNotFoundError):
            self.manager.store_file(Path("/nonexistent/file.txt"))

    def test_load_by_id(self) -> None:
        """Test loading artifact content by ID."""
        content = b"test content"
        ref = self.manager.store(content)
        loaded = self.manager.load_by_id(ref.metadata.artifact_id)
        assert loaded == content

    def test_load_by_id_missing(self) -> None:
        """Test loading a non-existent artifact by ID."""
        assert self.manager.load_by_id("nonexistent") is None

    def test_get_ref(self) -> None:
        """Test getting an ArtifactRef by ID."""
        content = b"test"
        ref = self.manager.store(content)
        retrieved = self.manager.get_ref(ref.metadata.artifact_id)
        assert retrieved is not None
        assert retrieved.hash == ref.hash
        assert retrieved.metadata.artifact_id == ref.metadata.artifact_id

    def test_get_ref_missing(self) -> None:
        """Test getting a non-existent ArtifactRef."""
        assert self.manager.get_ref("nonexistent") is None

    def test_deduplication(self) -> None:
        """Test that duplicate content shares the same storage."""
        content = b"duplicate content"
        ref1 = self.manager.store(content)
        ref2 = self.manager.store(content)

        # Different artifact IDs, same content hash and path
        assert ref1.artifact_id != ref2.artifact_id
        assert ref1.hash == ref2.hash
        assert ref1.path == ref2.path

    def test_compute_hash(self) -> None:
        """Test hash computation."""
        hash1 = ArtifactManager.compute_hash(b"hello")
        hash2 = ArtifactManager.compute_hash(b"hello")
        hash3 = ArtifactManager.compute_hash(b"world")

        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64  # SHA-256 hex

    def test_compute_file_hash(self) -> None:
        """Test file hash computation."""
        file_path = self.temp_dir / "hash_test.txt"
        file_path.write_bytes(b"hash me")

        file_hash = ArtifactManager.compute_file_hash(file_path)
        direct_hash = ArtifactManager.compute_hash(b"hash me")
        assert file_hash == direct_hash

    def test_list_artifacts(self) -> None:
        """Test listing artifacts."""
        assert len(self.manager.list_artifacts()) == 0
        self.manager.store(b"first", tags=["a"])
        self.manager.store(b"second", tags=["b"])
        assert len(self.manager.list_artifacts()) == 2

    def test_list_by_run(self) -> None:
        """Test listing artifacts by workflow run ID."""
        ref1 = self.manager.store(b"run1 artifact", workflow_run_id="run-1")
        ref2 = self.manager.store(b"run2 artifact", workflow_run_id="run-2")

        run1_artifacts = self.manager.list_by_run("run-1")
        assert len(run1_artifacts) == 1
        assert run1_artifacts[0].metadata.artifact_id == ref1.metadata.artifact_id

    def test_delete_artifact(self) -> None:
        """Test deleting artifact metadata."""
        ref = self.manager.store(b"to delete")
        assert self.manager.delete_artifact(ref.metadata.artifact_id)
        assert self.manager.get_ref(ref.metadata.artifact_id) is None

    def test_delete_nonexistent(self) -> None:
        """Test deleting a non-existent artifact."""
        assert not self.manager.delete_artifact("nonexistent")

    def test_verify_integrity(self) -> None:
        """Test integrity verification."""
        ref = self.manager.store(b"verify me")
        assert self.manager.verify_integrity(ref)

        # Corrupt the file
        ref.path.write_bytes(b"corrupted")
        assert not self.manager.verify_integrity(ref)

    def test_artifact_count(self) -> None:
        """Test the artifact_count property."""
        assert self.manager.artifact_count == 0
        self.manager.store(b"a")
        self.manager.store(b"b")
        assert self.manager.artifact_count == 2

    def test_metadata_fields(self) -> None:
        """Test that metadata fields are stored correctly."""
        ref = self.manager.store(
            b"test",
            source="unit test",
            workflow_run_id="run-1",
            step_name="build",
            content_type="text/plain",
            tags=["test", "example"],
            version="2.0.0",
            parent_ids=["parent-1"],
            metadata={"custom": "value"},
        )

        assert ref.metadata.source == "unit test"
        assert ref.metadata.workflow_run_id == "run-1"
        assert ref.metadata.step_name == "build"
        assert ref.metadata.content_type == "text/plain"
        assert ref.metadata.tags == ["test", "example"]
        assert ref.metadata.version == "2.0.0"
        assert ref.metadata.parent_ids == ["parent-1"]
        assert ref.metadata.metadata["custom"] == "value"
