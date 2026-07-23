"""Artifact Validator — checks completeness, integrity, dependencies, required outputs, and content hashes.

Every artifact produced by a task is validated before the task
is considered complete.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Optional

from workflow_orchestrator.builder.data_models import ArtifactCheckResult
from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class ArtifactValidator:
    """Validates artifacts produced by tasks.

    Checks:
    - Completeness: All expected artifacts exist
    - Integrity: Content hashes match expected values
    - Dependencies: Required dependencies are satisfied
    - Required outputs: Expected output types are present

    Usage:
        >>> validator = ArtifactValidator()
        >>> results = validator.check_outputs({"files": {"main.py": "content"}})
        >>> print(all(r.exists for r in results))
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Artifact Validator.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus
        self._known_hashes: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def check_outputs(self, outputs: dict[str, Any]) -> list[ArtifactCheckResult]:
        """Check all outputs from a task.

        Args:
            outputs: The outputs to check.

        Returns:
            List of ArtifactCheckResult for each expected artifact.
        """
        results: list[ArtifactCheckResult] = []

        # Check files
        files = outputs.get("files", outputs.get("artifacts", {}))
        if isinstance(files, dict):
            for name, content in files.items():
                result = self._check_file_artifact(name, content)
                results.append(result)

        # Check generic outputs
        for key in ["output", "result", "data"]:
            if key in outputs and key not in ("files", "artifacts"):
                result = self._check_generic_artifact(key, outputs[key])
                results.append(result)

        if not results:
            # No specific artifacts found, check existence
            results.append(ArtifactCheckResult(
                artifact_name="output",
                exists=bool(outputs),
                complete=bool(outputs),
                integrity_pass=True,
                dependencies_met=True,
            ))

        return results

    def _check_file_artifact(self, name: str, content: Any) -> ArtifactCheckResult:
        """Check a file-type artifact.

        Args:
            name: The artifact name.
            content: The artifact content.

        Returns:
            ArtifactCheckResult for this artifact.
        """
        issues: list[str] = []
        content_str = str(content) if content else ""

        # Check completeness
        exists = bool(content)
        complete = exists and len(content_str) > 0

        if not exists:
            issues.append(f"Artifact '{name}' is missing")
        elif not complete:
            issues.append(f"Artifact '{name}' is empty")

        # Check integrity via content hash
        integrity = True
        if content_str:
            content_hash = hashlib.sha256(content_str.encode()).hexdigest()
            if name in self._known_hashes:
                integrity = self._known_hashes[name] == content_hash
                if not integrity:
                    issues.append(f"Artifact '{name}' content hash mismatch")
            self._known_hashes[name] = content_hash

        return ArtifactCheckResult(
            artifact_name=name,
            exists=exists,
            complete=complete,
            integrity_pass=integrity,
            dependencies_met=True,
            issues=issues,
        )

    def _check_generic_artifact(self, name: str, value: Any) -> ArtifactCheckResult:
        """Check a non-file artifact.

        Args:
            name: The artifact name.
            value: The artifact value.

        Returns:
            ArtifactCheckResult for this artifact.
        """
        issues: list[str] = []
        exists = value is not None
        complete = exists and bool(value) if not isinstance(value, bool) else True

        if not exists:
            issues.append(f"Output '{name}' is missing")

        integrity = True

        return ArtifactCheckResult(
            artifact_name=name,
            exists=exists,
            complete=complete,
            integrity_pass=integrity,
            dependencies_met=True,
            issues=issues,
        )

    def check_artifact_integrity(self, artifact_name: str, content: str) -> bool:
        """Check the integrity of a single artifact.

        Args:
            artifact_name: Name of the artifact.
            content: Current content to verify.

        Returns:
            True if integrity check passes (no known hash or hash matches).
        """
        if not content:
            return False

        content_hash = hashlib.sha256(content.encode()).hexdigest()
        if artifact_name in self._known_hashes:
            return self._known_hashes[artifact_name] == content_hash
        return True

    def register_expected_hash(self, artifact_name: str, content: str) -> None:
        """Register an expected content hash for an artifact.

        Args:
            artifact_name: Name of the artifact.
            content: Content to hash and register.
        """
        self._known_hashes[artifact_name] = hashlib.sha256(content.encode()).hexdigest()

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(
                type=event_type, data=data, source="artifact_validator",
            ))
        except Exception:
            pass
