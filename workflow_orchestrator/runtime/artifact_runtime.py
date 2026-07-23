"""Artifact Runtime — manages provider/agent outputs as versioned artifacts.

Every provider and agent output becomes a content-addressed artifact
with SHA256 hash, metadata, provenance tracking, and session binding.
Never passes raw files between providers — only artifact references.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.core.artifact_manager import ArtifactManager, ArtifactMetadata, ArtifactRef

logger = logging.getLogger(__name__)


class ArtifactRuntime:
    """Runtime for artifact management with provider/agent provenance.

    Extends ArtifactManager with provider/agent tracking, session
    binding, dependency tracking, and origin prompt recording.

    Usage:
        >>> runtime = ArtifactRuntime(artifact_manager)
        >>> ref = runtime.store_provider_output(
        ...     content=b"generated code",
        ...     provider_id="anthropic.claude",
        ...     agent_id="claude-code",
        ...     session_id="session-123",
        ...     origin_prompt="Generate a login page",
        ... )
        >>> deps = runtime.get_artifact_dependencies(ref.artifact_id)
    """

    def __init__(
        self,
        artifact_manager: ArtifactManager,
        event_bus: Any = None,
    ) -> None:
        """Initialize the Artifact Runtime.

        Args:
            artifact_manager: The artifact manager for content-addressed storage.
            event_bus: Optional EventBus for publishing events.
        """
        self._artifact_manager = artifact_manager
        self._event_bus = event_bus
        self._dependencies: dict[str, list[str]] = {}  # artifact_id -> parent_ids
        self._provenance: dict[str, dict[str, str]] = {}  # artifact_id -> provenance

    @property
    def artifact_manager(self) -> ArtifactManager:
        """The underlying artifact manager."""
        return self._artifact_manager

    # ------------------------------------------------------------------
    # Store provider/agent outputs
    # ------------------------------------------------------------------

    def store_provider_output(
        self,
        content: bytes,
        provider_id: str,
        agent_id: str = "",
        session_id: str = "",
        origin_prompt: str = "",
        parent_ids: list[str] | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRef:
        """Store a provider's output as an artifact.

        Args:
            content: The output content bytes.
            provider_id: The provider that generated this output.
            agent_id: The agent that generated this output.
            session_id: The session this artifact belongs to.
            origin_prompt: The prompt that generated this artifact.
            parent_ids: IDs of artifacts this was derived from.
            tags: Optional tags for filtering.
            metadata: Additional metadata.

        Returns:
            ArtifactRef for the stored artifact.
        """
        artifact_meta = metadata or {}
        artifact_meta.update({
            "provider_id": provider_id,
            "agent_id": agent_id,
            "origin_prompt": origin_prompt,
        })

        ref = self._artifact_manager.store(
            content=content,
            source=f"provider:{provider_id}",
            workflow_run_id=session_id,
            step_name=agent_id or provider_id,
            content_type="text/plain",
            tags=["provider_output", provider_id, *(tags or [])],
            parent_ids=parent_ids or [],
            metadata=artifact_meta,
        )

        # Track provenance and dependencies
        self._provenance[ref.artifact_id] = {
            "provider_id": provider_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "origin_prompt": origin_prompt[:200] if origin_prompt else "",
            "stored_at": datetime.now(timezone.utc).isoformat(),
        }

        if parent_ids:
            self._dependencies[ref.artifact_id] = list(parent_ids)

        self._publish_event("artifact.created", {
            "artifact_id": ref.artifact_id,
            "hash": ref.hash[:12],
            "provider_id": provider_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "size_bytes": len(content),
        })

        logger.debug(
            "Stored provider artifact '%s' from %s/%s (%d bytes)",
            ref.artifact_id, provider_id, agent_id or "none", len(content),
        )
        return ref

    def store_agent_output(
        self,
        content: bytes,
        agent_id: str,
        provider_id: str = "",
        session_id: str = "",
        origin_prompt: str = "",
        parent_ids: list[str] | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRef:
        """Store an agent's output as an artifact.

        Args:
            content: The output content bytes.
            agent_id: The agent that generated this output.
            provider_id: The provider used.
            session_id: The session this artifact belongs to.
            origin_prompt: The prompt that generated this artifact.
            parent_ids: IDs of artifacts this was derived from.
            tags: Optional tags for filtering.
            metadata: Additional metadata.

        Returns:
            ArtifactRef for the stored artifact.
        """
        return self.store_provider_output(
            content=content,
            provider_id=provider_id,
            agent_id=agent_id,
            session_id=session_id,
            origin_prompt=origin_prompt,
            parent_ids=parent_ids,
            tags=["agent_output", agent_id, *(tags or [])],
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Retrieve artifacts
    # ------------------------------------------------------------------

    def load(self, ref: ArtifactRef) -> bytes:
        """Load artifact content by reference.

        Args:
            ref: The ArtifactRef to load.

        Returns:
            The artifact content bytes.
        """
        return self._artifact_manager.load(ref)

    def load_by_id(self, artifact_id: str) -> Optional[bytes]:
        """Load artifact content by ID.

        Args:
            artifact_id: The artifact identifier.

        Returns:
            The content bytes, or None.
        """
        return self._artifact_manager.load_by_id(artifact_id)

    def get_ref(self, artifact_id: str) -> Optional[ArtifactRef]:
        """Get an ArtifactRef by ID without loading content.

        Args:
            artifact_id: The artifact identifier.

        Returns:
            ArtifactRef or None.
        """
        return self._artifact_manager.get_ref(artifact_id)

    def get_metadata(self, artifact_id: str) -> ArtifactMetadata | None:
        """Get metadata for an artifact.

        Args:
            artifact_id: The artifact identifier.

        Returns:
            ArtifactMetadata, or None.
        """
        ref = self._artifact_manager.get_ref(artifact_id)
        if ref is None:
            return None
        return ref.metadata

    # ------------------------------------------------------------------
    # Provenance tracking
    # ------------------------------------------------------------------

    def get_provenance(self, artifact_id: str) -> dict[str, str] | None:
        """Get provenance information for an artifact.

        Args:
            artifact_id: The artifact identifier.

        Returns:
            Provenance dict, or None.
        """
        return self._provenance.get(artifact_id)

    def get_artifact_dependencies(self, artifact_id: str) -> list[str]:
        """Get the parent artifact IDs for an artifact.

        Args:
            artifact_id: The artifact identifier.

        Returns:
            List of parent artifact IDs.
        """
        return list(self._dependencies.get(artifact_id, []))

    def get_artifact_chain(self, artifact_id: str) -> list[str]:
        """Get the full ancestry chain for an artifact.

        Args:
            artifact_id: The artifact identifier.

        Returns:
            List of artifact IDs from oldest ancestor to this artifact.
        """
        chain: list[str] = []
        current = artifact_id
        visited: set[str] = set()

        while current and current not in visited:
            visited.add(current)
            chain.insert(0, current)
            parents = self._dependencies.get(current, [])
            current = parents[0] if parents else ""

        return chain

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    def list_by_session(self, session_id: str) -> list[ArtifactRef]:
        """List all artifacts for a session.

        Args:
            session_id: The session identifier.

        Returns:
            List of ArtifactRef objects.
        """
        return self._artifact_manager.list_by_run(session_id)

    def list_by_provider(self, provider_id: str) -> list[ArtifactRef]:
        """List all artifacts from a specific provider.

        Args:
            provider_id: The provider identifier.

        Returns:
            List of ArtifactRef objects.
        """
        all_artifacts = self._artifact_manager.list_artifacts(limit=1000)
        return [
            ref for ref in self._get_all_refs(all_artifacts)
            if ref.metadata.metadata.get("provider_id") == provider_id
        ]

    def list_recent(self, limit: int = 20) -> list[ArtifactRef]:
        """List the most recent artifacts.

        Args:
            limit: Maximum number to return.

        Returns:
            List of recent ArtifactRef objects.
        """
        metadatas = self._artifact_manager.list_artifacts(limit=limit)
        return [
            ref for ref in self._get_all_refs(metadatas)
        ][:limit]

    def _get_all_refs(self, metadatas: list[ArtifactMetadata]) -> list[ArtifactRef]:
        """Convert metadata list to ArtifactRef list.

        Args:
            metadatas: List of ArtifactMetadata.

        Returns:
            List of ArtifactRef objects.
        """
        refs: list[ArtifactRef] = []
        for meta in metadatas:
            ref = self._artifact_manager.get_ref(meta.artifact_id)
            if ref:
                refs.append(ref)
        return refs

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def verify_integrity(self, artifact_id: str) -> bool:
        """Verify that an artifact's content matches its hash.

        Args:
            artifact_id: The artifact identifier.

        Returns:
            True if the content hash matches.
        """
        ref = self._artifact_manager.get_ref(artifact_id)
        if ref is None:
            return False
        return self._artifact_manager.verify_integrity(ref)

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an artifact event.

        Args:
            event_type: The event type string.
            data: Event payload.
        """
        if self._event_bus is None:
            return
        try:
            from workflow_orchestrator.core.event_bus import Event
            self._event_bus.publish(Event(type=event_type, data=data, source="artifact_runtime"))
        except Exception:
            pass
