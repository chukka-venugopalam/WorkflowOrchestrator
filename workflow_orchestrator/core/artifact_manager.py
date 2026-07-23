"""Artifact manager for content-addressed artifact storage.

Manages artifacts produced during workflow execution with
content-addressed storage, versioning, metadata, and provenance
tracking.  Local filesystem storage only — no remote backends.

Key concepts:
- Artifacts are content-addressed (SHA-256 hash as identifier)
- Versioning: each artifact tracks its lineage
- Metadata: every artifact stores creation time, source, and tags
- Relationships: artifacts can reference each other
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ArtifactMetadata:
    """Metadata stored alongside each artifact.

    Attributes:
        artifact_id: Unique artifact identifier.
        hash: SHA-256 hash of the artifact content.
        size_bytes: Size of the artifact in bytes.
        created_at: ISO-8601 creation timestamp.
        source: Description of what created this artifact (e.g., step name).
        workflow_run_id: The run that produced this artifact.
        step_name: The step name that produced this artifact.
        content_type: MIME type or content category.
        tags: Arbitrary tags for filtering.
        version: Version string for this artifact lineage.
        parent_ids: IDs of artifacts this one was derived from.
        metadata: Additional implementation-specific metadata.
    """

    artifact_id: str
    hash: str = ""
    size_bytes: int = 0
    created_at: str = ""
    source: str = ""
    workflow_run_id: str = ""
    step_name: str = ""
    content_type: str = "application/octet-stream"
    tags: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    parent_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "artifact_id": self.artifact_id,
            "hash": self.hash,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at,
            "source": self.source,
            "workflow_run_id": self.workflow_run_id,
            "step_name": self.step_name,
            "content_type": self.content_type,
            "tags": self.tags,
            "version": self.version,
            "parent_ids": self.parent_ids,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArtifactMetadata:
        """Create from a dictionary."""
        return cls(
            artifact_id=data.get("artifact_id", uuid.uuid4().hex[:12]),
            hash=data.get("hash", ""),
            size_bytes=data.get("size_bytes", 0),
            created_at=data.get("created_at", ""),
            source=data.get("source", ""),
            workflow_run_id=data.get("workflow_run_id", ""),
            step_name=data.get("step_name", ""),
            content_type=data.get("content_type", "application/octet-stream"),
            tags=data.get("tags", []),
            version=data.get("version", "1.0.0"),
            parent_ids=data.get("parent_ids", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ArtifactRef:
    """A reference to an artifact.

    This is used to pass artifact references between components
    without loading the full content.

    Attributes:
        artifact_id: The artifact's unique ID.
        hash: The content hash (for integrity verification).
        path: Filesystem path to the artifact content.
        metadata: The artifact's metadata.
    """

    artifact_id: str
    hash: str
    path: Path
    metadata: ArtifactMetadata


class ArtifactManager:
    """Manages artifacts with content-addressed storage.

    Stores artifacts in a local directory structure:
    ``{base_path}/{hash[:2]}/{hash[2:4]}/{hash}``

    Usage:
        >>> manager = ArtifactManager(base_path=Path("/tmp/artifacts"))
        >>> ref = manager.store(b"hello world", source="test", tags=["example"])
        >>> content = manager.load(ref)
        >>> print(content)
        b'hello world'
    """

    def __init__(self, base_path: Path | str) -> None:
        """Initialize the artifact manager.

        Args:
            base_path: Root directory for artifact storage.
        """
        self._base_path = Path(base_path).expanduser().resolve()
        self._base_path.mkdir(parents=True, exist_ok=True)
        self._metadata_dir = self._base_path / ".metadata"
        self._metadata_dir.mkdir(parents=True, exist_ok=True)

    @property
    def base_path(self) -> Path:
        """The base directory for artifact storage."""
        return self._base_path

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    @staticmethod
    def compute_hash(content: bytes) -> str:
        """Compute the SHA-256 hash of content.

        Args:
            content: The content bytes.

        Returns:
            Hex-encoded SHA-256 hash.
        """
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def compute_file_hash(path: Path) -> str:
        """Compute the SHA-256 hash of a file.

        Args:
            path: Path to the file.

        Returns:
            Hex-encoded SHA-256 hash.
        """
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    def store(
        self,
        content: bytes,
        *,
        source: str = "",
        workflow_run_id: str = "",
        step_name: str = "",
        content_type: str = "application/octet-stream",
        tags: list[str] | None = None,
        version: str = "1.0.0",
        parent_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRef:
        """Store content as an artifact.

        Args:
            content: The content bytes to store.
            source: Description of what created this artifact.
            workflow_run_id: The run that produced this artifact.
            step_name: The step name that produced this artifact.
            content_type: MIME type or content category.
            tags: Optional tags for filtering.
            version: Version string.
            parent_ids: IDs of parent artifacts.
            metadata: Additional metadata.

        Returns:
            An ArtifactRef for the stored artifact.
        """
        content_hash = self.compute_hash(content)
        artifact_id = uuid.uuid4().hex[:12]

        # Content-addressed storage path
        artifact_dir = self._base_path / content_hash[:2] / content_hash[2:4]
        artifact_dir.mkdir(parents=True, exist_ok=True)

        # Check for duplicate content
        artifact_path = artifact_dir / content_hash
        if not artifact_path.exists():
            artifact_path.write_bytes(content)

        # Create metadata
        now = datetime.now(timezone.utc).isoformat()
        meta = ArtifactMetadata(
            artifact_id=artifact_id,
            hash=content_hash,
            size_bytes=len(content),
            created_at=now,
            source=source,
            workflow_run_id=workflow_run_id,
            step_name=step_name,
            content_type=content_type,
            tags=tags or [],
            version=version,
            parent_ids=parent_ids or [],
            metadata=metadata or {},
        )

        # Save metadata
        self._save_metadata(artifact_id, meta)

        ref = ArtifactRef(
            artifact_id=artifact_id,
            hash=content_hash,
            path=artifact_path,
            metadata=meta,
        )

        logger.debug(
            "Stored artifact '%s' (hash=%s..., size=%d bytes)",
            artifact_id,
            content_hash[:8],
            len(content),
        )
        return ref

    def store_file(
        self,
        file_path: Path | str,
        *,
        source: str = "",
        workflow_run_id: str = "",
        step_name: str = "",
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> ArtifactRef:
        """Store a file as an artifact.

        Args:
            file_path: Path to the file to store.
            source: Description of what created this artifact.
            workflow_run_id: The run that produced this artifact.
            step_name: The step name that produced this artifact.
            tags: Optional tags for filtering.
            **kwargs: Additional metadata passed to ``store()``.

        Returns:
            An ArtifactRef for the stored artifact.
        """
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        content = path.read_bytes()
        return self.store(
            content,
            source=source or str(path),
            workflow_run_id=workflow_run_id,
            step_name=step_name,
            tags=tags or [],
            **kwargs,
        )

    def load(self, ref: ArtifactRef) -> bytes:
        """Load artifact content by reference.

        Args:
            ref: The ArtifactRef to load.

        Returns:
            The artifact content bytes.

        Raises:
            FileNotFoundError: If the artifact file is missing.
        """
        if not ref.path.exists():
            raise FileNotFoundError(f"Artifact content not found: {ref.path}")
        return ref.path.read_bytes()

    def load_by_id(self, artifact_id: str) -> Optional[bytes]:
        """Load artifact content by ID.

        Args:
            artifact_id: The artifact identifier.

        Returns:
            The content bytes, or None if not found.
        """
        meta = self._load_metadata(artifact_id)
        if meta is None:
            return None

        artifact_path = self._base_path / meta.hash[:2] / meta.hash[2:4] / meta.hash
        if not artifact_path.exists():
            return None
        return artifact_path.read_bytes()

    def get_ref(self, artifact_id: str) -> Optional[ArtifactRef]:
        """Get an ArtifactRef by ID without loading content.

        Args:
            artifact_id: The artifact identifier.

        Returns:
            ArtifactRef or None if not found.
        """
        meta = self._load_metadata(artifact_id)
        if meta is None:
            return None

        artifact_path = self._base_path / meta.hash[:2] / meta.hash[2:4] / meta.hash
        return ArtifactRef(
            artifact_id=artifact_id,
            hash=meta.hash,
            path=artifact_path,
            metadata=meta,
        )

    # ------------------------------------------------------------------
    # Metadata management
    # ------------------------------------------------------------------

    def _save_metadata(self, artifact_id: str, meta: ArtifactMetadata) -> None:
        """Persist artifact metadata."""
        meta_file = self._metadata_dir / f"{artifact_id}.json"
        meta_file.write_text(json.dumps(meta.to_dict(), indent=2), encoding="utf-8")

    def _load_metadata(self, artifact_id: str) -> Optional[ArtifactMetadata]:
        """Load artifact metadata by ID."""
        meta_file = self._metadata_dir / f"{artifact_id}.json"
        if not meta_file.exists():
            return None
        try:
            data = json.loads(meta_file.read_text(encoding="utf-8"))
            return ArtifactMetadata.from_dict(data)
        except (json.JSONDecodeError, OSError):
            return None

    def list_artifacts(self, limit: int = 100) -> list[ArtifactMetadata]:
        """List stored artifacts, newest first.

        Args:
            limit: Maximum number to return.

        Returns:
            List of ArtifactMetadata objects.
        """
        if not self._metadata_dir.exists():
            return []

        artifacts: list[ArtifactMetadata] = []
        for meta_file in sorted(self._metadata_dir.glob("*.json"), reverse=True):
            meta = self._load_metadata(meta_file.stem)
            if meta:
                artifacts.append(meta)
            if len(artifacts) >= limit:
                break

        return artifacts

    def list_by_run(self, workflow_run_id: str) -> list[ArtifactRef]:
        """List all artifacts for a specific run.

        Args:
            workflow_run_id: The run identifier.

        Returns:
            List of ArtifactRef objects.
        """
        results: list[ArtifactRef] = []
        for meta_file in self._metadata_dir.glob("*.json"):
            meta = self._load_metadata(meta_file.stem)
            if meta and meta.workflow_run_id == workflow_run_id:
                artifact_path = self._base_path / meta.hash[:2] / meta.hash[2:4] / meta.hash
                results.append(ArtifactRef(
                    artifact_id=meta.artifact_id,
                    hash=meta.hash,
                    path=artifact_path,
                    metadata=meta,
                ))
        return results

    def delete_artifact(self, artifact_id: str) -> bool:
        """Delete an artifact's metadata (keeps content for deduplication).

        Args:
            artifact_id: The artifact identifier.

        Returns:
            True if deleted, False if not found.
        """
        meta_file = self._metadata_dir / f"{artifact_id}.json"
        if not meta_file.exists():
            return False
        meta_file.unlink()
        return True

    def verify_integrity(self, ref: ArtifactRef) -> bool:
        """Verify that stored content matches its hash.

        Args:
            ref: The ArtifactRef to verify.

        Returns:
            True if content hash matches.
        """
        if not ref.path.exists():
            return False
        actual_hash = self.compute_file_hash(ref.path)
        return actual_hash == ref.hash

    @property
    def artifact_count(self) -> int:
        """Total number of artifacts with metadata."""
        if not self._metadata_dir.exists():
            return 0
        return len(list(self._metadata_dir.glob("*.json")))
