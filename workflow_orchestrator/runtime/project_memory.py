"""Project Memory — manages the ``.state/`` directory for persistent project memory.

Every project creates a ``.state/`` directory with:
- session.json — current session state
- providers.json — provider configuration
- agents.json — agent configuration
- timeline.json — execution timeline
- artifacts/ — artifact storage
- history/ — execution history
- summaries/ — stored summaries
- contract/ — contract version tracking
- context/ — context snapshots

This becomes reusable for future executions.
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.intelligence.models import ArtifactReference

logger = logging.getLogger(__name__)


class ProjectMemory:
    """Manages the ``.state/`` directory for persistent project memory.

    Provides structured access to all project-level state including
    session data, provider/agent configs, execution timelines,
    artifacts, history, summaries, contracts, and context snapshots.

    Usage:
        >>> memory = ProjectMemory(Path("./my-project"))
        >>> memory.initialize()
        >>> memory.save_session({"session_id": "abc", "state": "active"})
        >>> data = memory.load_session()
    """

    def __init__(self, project_dir: Path | str) -> None:
        """Initialize Project Memory.

        Args:
            project_dir: Root directory of the project.
        """
        self._project_dir = Path(project_dir).expanduser().resolve()
        self._state_dir = self._project_dir / ".state"

    @property
    def project_dir(self) -> Path:
        """The project root directory."""
        return self._project_dir

    @property
    def state_dir(self) -> Path:
        """The .state directory path."""
        return self._state_dir

    # ------------------------------------------------------------------
    # Directory structure
    # ------------------------------------------------------------------

    STATE_SUBDIRS = [
        "artifacts",
        "history",
        "summaries",
        "contract",
        "context",
    ]

    def initialize(self) -> None:
        """Create the .state directory structure if it doesn't exist."""
        self._state_dir.mkdir(parents=True, exist_ok=True)
        for subdir in self.STATE_SUBDIRS:
            (self._state_dir / subdir).mkdir(exist_ok=True)
        logger.debug("Project memory initialized at %s", self._state_dir)

    def exists(self) -> bool:
        """Check if the .state directory exists.

        Returns:
            True if the .state directory exists.
        """
        return self._state_dir.exists()

    def clear(self) -> None:
        """Clear all project memory data."""
        if self._state_dir.exists():
            shutil.rmtree(self._state_dir)
            logger.info("Project memory cleared at %s", self._state_dir)

    # ------------------------------------------------------------------
    # Session persistence
    # ------------------------------------------------------------------

    def save_session(self, data: dict[str, Any]) -> None:
        """Save session data to session.json.

        Args:
            data: Session data to persist.
        """
        self.initialize()
        self._write_json("session.json", data)

    def load_session(self) -> dict[str, Any] | None:
        """Load session data from session.json.

        Returns:
            Session data dict, or None.
        """
        return self._read_json("session.json")

    # ------------------------------------------------------------------
    # Provider persistence
    # ------------------------------------------------------------------

    def save_providers(self, providers: list[dict[str, Any]]) -> None:
        """Save provider configuration to providers.json.

        Args:
            providers: List of provider config dicts.
        """
        self.initialize()
        self._write_json("providers.json", {"providers": providers, "updated_at": datetime.now(timezone.utc).isoformat()})

    def load_providers(self) -> list[dict[str, Any]]:
        """Load provider configuration from providers.json.

        Returns:
            List of provider config dicts.
        """
        data = self._read_json("providers.json")
        return data.get("providers", []) if data else []

    # ------------------------------------------------------------------
    # Agent persistence
    # ------------------------------------------------------------------

    def save_agents(self, agents: list[dict[str, Any]]) -> None:
        """Save agent configuration to agents.json.

        Args:
            agents: List of agent config dicts.
        """
        self.initialize()
        self._write_json("agents.json", {"agents": agents, "updated_at": datetime.now(timezone.utc).isoformat()})

    def load_agents(self) -> list[dict[str, Any]]:
        """Load agent configuration from agents.json.

        Returns:
            List of agent config dicts.
        """
        data = self._read_json("agents.json")
        return data.get("agents", []) if data else []

    # ------------------------------------------------------------------
    # Timeline persistence
    # ------------------------------------------------------------------

    def save_timeline(self, entries: list[dict[str, Any]]) -> None:
        """Save execution timeline to timeline.json.

        Args:
            entries: List of timeline entry dicts.
        """
        self.initialize()
        self._write_json("timeline.json", {"entries": entries, "updated_at": datetime.now(timezone.utc).isoformat()})

    def load_timeline(self) -> list[dict[str, Any]]:
        """Load execution timeline from timeline.json.

        Returns:
            List of timeline entry dicts.
        """
        data = self._read_json("timeline.json")
        return data.get("entries", []) if data else []

    def append_timeline_entry(self, entry: dict[str, Any]) -> None:
        """Append a single entry to the timeline.

        Args:
            entry: Timeline entry dict to append.
        """
        entries = self.load_timeline()
        entries.append(entry)
        self.save_timeline(entries)

    # ------------------------------------------------------------------
    # Artifact tracking
    # ------------------------------------------------------------------

    def save_artifact_metadata(self, artifact_id: str, data: dict[str, Any]) -> None:
        """Save artifact metadata to artifacts/.

        Args:
            artifact_id: The artifact identifier.
            data: Artifact metadata dict.
        """
        self.initialize()
        artifact_file = self._state_dir / "artifacts" / f"{artifact_id}.json"
        artifact_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load_artifact_metadata(self, artifact_id: str) -> dict[str, Any] | None:
        """Load artifact metadata from artifacts/.

        Args:
            artifact_id: The artifact identifier.

        Returns:
            Artifact metadata dict, or None.
        """
        artifact_file = self._state_dir / "artifacts" / f"{artifact_id}.json"
        if not artifact_file.exists():
            return None
        try:
            return json.loads(artifact_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def list_artifact_ids(self) -> list[str]:
        """List all stored artifact IDs.

        Returns:
            Sorted list of artifact IDs.
        """
        artifacts_dir = self._state_dir / "artifacts"
        if not artifacts_dir.exists():
            return []
        return sorted(p.stem for p in artifacts_dir.glob("*.json"))

    # ------------------------------------------------------------------
    # History persistence
    # ------------------------------------------------------------------

    def save_history(self, session_id: str, entries: list[dict[str, Any]]) -> None:
        """Save execution history to history/.

        Args:
            session_id: The session identifier.
            entries: List of history entry dicts.
        """
        self.initialize()
        history_file = self._state_dir / "history" / f"{session_id}.json"
        history_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    def load_history(self, session_id: str) -> list[dict[str, Any]]:
        """Load execution history from history/.

        Args:
            session_id: The session identifier.

        Returns:
            List of history entry dicts.
        """
        history_file = self._state_dir / "history" / f"{session_id}.json"
        if not history_file.exists():
            return []
        try:
            return json.loads(history_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    # ------------------------------------------------------------------
    # Summary persistence
    # ------------------------------------------------------------------

    def save_summary(self, summary_id: str, content: str) -> None:
        """Save a summary to summaries/.

        Args:
            summary_id: Summary identifier.
            content: Summary content.
        """
        self.initialize()
        summary_file = self._state_dir / "summaries" / f"{summary_id}.txt"
        summary_file.write_text(content, encoding="utf-8")

    def load_summary(self, summary_id: str) -> str | None:
        """Load a summary from summaries/.

        Args:
            summary_id: Summary identifier.

        Returns:
            Summary content, or None.
        """
        summary_file = self._state_dir / "summaries" / f"{summary_id}.txt"
        if not summary_file.exists():
            return None
        return summary_file.read_text(encoding="utf-8")

    def list_summaries(self) -> list[str]:
        """List all summary IDs.

        Returns:
            Sorted list of summary IDs.
        """
        summaries_dir = self._state_dir / "summaries"
        if not summaries_dir.exists():
            return []
        return sorted(p.stem for p in summaries_dir.glob("*.txt"))

    # ------------------------------------------------------------------
    # Contract persistence
    # ------------------------------------------------------------------

    def save_contract(self, data: dict[str, Any]) -> None:
        """Save contract version data to contract/.

        Args:
            data: Contract data dict.
        """
        self.initialize()
        self._write_json("contract/version.json", data)

    def load_contract(self) -> dict[str, Any] | None:
        """Load contract version data from contract/.

        Returns:
            Contract data dict, or None.
        """
        return self._read_json("contract/version.json")

    # ------------------------------------------------------------------
    # Context persistence
    # ------------------------------------------------------------------

    def save_context_snapshot(self, snapshot_id: str, data: dict[str, Any]) -> None:
        """Save a context snapshot to context/.

        Args:
            snapshot_id: Snapshot identifier.
            data: Context snapshot data.
        """
        self.initialize()
        snapshot_file = self._state_dir / "context" / f"{snapshot_id}.json"
        snapshot_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load_context_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        """Load a context snapshot from context/.

        Args:
            snapshot_id: Snapshot identifier.

        Returns:
            Context snapshot data, or None.
        """
        snapshot_file = self._state_dir / "context" / f"{snapshot_id}.json"
        if not snapshot_file.exists():
            return None
        try:
            return json.loads(snapshot_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    # ------------------------------------------------------------------
    # File helpers
    # ------------------------------------------------------------------

    def _write_json(self, relative_path: str, data: dict[str, Any]) -> None:
        """Write JSON data to a file relative to .state/.

        Args:
            relative_path: Path relative to .state/ directory.
            data: JSON-serializable data.
        """
        path = self._state_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("Failed to write %s: %s", relative_path, exc)

    def _read_json(self, relative_path: str) -> dict[str, Any] | None:
        """Read JSON data from a file relative to .state/.

        Args:
            relative_path: Path relative to .state/ directory.

        Returns:
            Parsed JSON data, or None.
        """
        path = self._state_dir / relative_path
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read %s: %s", relative_path, exc)
            return None
