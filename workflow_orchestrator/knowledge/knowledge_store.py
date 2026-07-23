"""Knowledge store — in-memory and file-backed knowledge storage.

No databases, no vector stores — simple deterministic storage.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.knowledge.knowledge_models import (
    KnowledgeCategory,
    KnowledgeEntry,
)

logger = logging.getLogger(__name__)


class KnowledgeStore:
    """In-memory storage for knowledge entries with optional file persistence.

    Usage:
        >>> store = KnowledgeStore()
        >>> entry = store.create("My Title", "Content...", KnowledgeCategory.GENERAL)
        >>> found = store.get(entry.entry_id)
    """

    def __init__(self, file_path: Path | str | None = None) -> None:
        """Initialize the knowledge store.

        Args:
            file_path: Optional file path for persistence.
        """
        self._entries: dict[str, KnowledgeEntry] = {}
        self._file_path = Path(file_path) if file_path else None

        if self._file_path and self._file_path.exists():
            self._load()

    def create(
        self,
        title: str,
        content: str,
        category: KnowledgeCategory = KnowledgeCategory.GENERAL,
        tags: list[str] | None = None,
        source: str = "",
    ) -> KnowledgeEntry:
        """Create a new knowledge entry.

        Args:
            title: Entry title.
            content: Entry content.
            category: Knowledge category.
            tags: Searchable tags.
            source: Source description.

        Returns:
            The created KnowledgeEntry.
        """
        now = datetime.now(timezone.utc).isoformat()
        entry = KnowledgeEntry(
            entry_id=uuid.uuid4().hex[:12],
            title=title,
            content=content,
            category=category,
            tags=tags or [],
            source=source,
            created_at=now,
            updated_at=now,
        )
        self._entries[entry.entry_id] = entry
        self._save()
        return entry

    def get(self, entry_id: str) -> KnowledgeEntry | None:
        """Get an entry by ID.

        Args:
            entry_id: The entry identifier.

        Returns:
            The KnowledgeEntry, or None.
        """
        return self._entries.get(entry_id)

    def update(
        self,
        entry_id: str,
        content: str | None = None,
        tags: list[str] | None = None,
    ) -> KnowledgeEntry | None:
        """Update an existing entry.

        Args:
            entry_id: The entry to update.
            content: New content (None = unchanged).
            tags: New tags (None = unchanged).

        Returns:
            The updated entry, or None if not found.
        """
        entry = self._entries.get(entry_id)
        if entry is None:
            return None

        if content is not None:
            entry.content = content
        if tags is not None:
            entry.tags = tags

        entry.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()
        return entry

    def remove(self, entry_id: str) -> bool:
        """Remove an entry.

        Args:
            entry_id: The entry to remove.

        Returns:
            True if removed.
        """
        result = self._entries.pop(entry_id, None) is not None
        if result:
            self._save()
        return result

    def list_by_category(self, category: KnowledgeCategory) -> list[KnowledgeEntry]:
        """List entries in a category.

        Args:
            category: The category to filter by.

        Returns:
            List of matching entries.
        """
        return [e for e in self._entries.values() if e.category == category]

    def list_all(self) -> list[KnowledgeEntry]:
        """List all entries.

        Returns:
            List of all entries.
        """
        return list(self._entries.values())

    def _save(self) -> None:
        """Persist entries to file."""
        if self._file_path is None:
            return
        try:
            data = {}
            for eid, entry in self._entries.items():
                data[eid] = {
                    "entry_id": entry.entry_id,
                    "title": entry.title,
                    "content": entry.content,
                    "category": entry.category.value,
                    "tags": entry.tags,
                    "source": entry.source,
                    "version": entry.version,
                    "created_at": entry.created_at,
                    "updated_at": entry.updated_at,
                }
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            self._file_path.write_text(json.dumps(data, indent=2))
        except OSError as exc:
            logger.warning("Failed to save knowledge store: %s", exc)

    def _load(self) -> None:
        """Load entries from file."""
        if self._file_path is None or not self._file_path.exists():
            return
        try:
            data = json.loads(self._file_path.read_text())
            for eid, item in data.items():
                try:
                    category = KnowledgeCategory(item.get("category", "general"))
                except ValueError:
                    category = KnowledgeCategory.GENERAL

                self._entries[eid] = KnowledgeEntry(
                    entry_id=item.get("entry_id", eid),
                    title=item.get("title", ""),
                    content=item.get("content", ""),
                    category=category,
                    tags=item.get("tags", []),
                    source=item.get("source", ""),
                    version=item.get("version", "1.0.0"),
                    created_at=item.get("created_at", ""),
                    updated_at=item.get("updated_at", ""),
                )
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load knowledge store: %s", exc)

    @property
    def count(self) -> int:
        """Number of entries."""
        return len(self._entries)
