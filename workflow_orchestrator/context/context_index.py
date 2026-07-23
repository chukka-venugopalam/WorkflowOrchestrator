"""Context index — fast index for context content lookup and reuse.

Provides deterministic indexing of context content with:
- Key-based lookups
- Layer-scoped queries
- Content deduplication
- Tag-based filtering
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from workflow_orchestrator.context.context_models import (
    ContextIndexEntry,
    ContextLayer,
    ContextLayerContent,
)

logger = logging.getLogger(__name__)


class ContextIndex:
    """Index for context content with fast lookups and deduplication.

    Usage:
        >>> index = ContextIndex()
        >>> index.index("key1", ContextLayer.WORKFLOW_STATE, "content...")
        >>> entry = index.lookup("key1")
        >>> results = index.search("workflow")
    """

    def __init__(self) -> None:
        self._entries: dict[str, ContextIndexEntry] = {}
        self._layer_index: dict[ContextLayer, list[str]] = {layer: [] for layer in ContextLayer}

    def index(
        self,
        key: str,
        layer: ContextLayer,
        content: str = "",
        tags: list[str] | None = None,
    ) -> ContextIndexEntry:
        """Index a piece of context content.

        Args:
            key: Unique lookup key.
            layer: Which layer this content belongs to.
            content: The content to index.
            tags: Optional categorization tags.

        Returns:
            The created ContextIndexEntry.
        """
        entry = ContextIndexEntry(
            key=key,
            layer=layer,
            content_preview=content[:200],
            token_count=len(content) // 4,
            created_at=datetime.now(timezone.utc).isoformat(),
            tags=tags or [],
        )
        self._entries[key] = entry
        if layer not in self._layer_index:
            self._layer_index[layer] = []
        self._layer_index[layer].append(key)
        return entry

    def lookup(self, key: str) -> ContextIndexEntry | None:
        """Look up an entry by key.

        Args:
            key: The entry key.

        Returns:
            The entry, or None if not found.
        """
        return self._entries.get(key)

    def lookup_by_layer(self, layer: ContextLayer) -> list[ContextIndexEntry]:
        """Get all entries for a specific layer.

        Args:
            layer: The layer to filter by.

        Returns:
            List of entries in that layer.
        """
        keys = self._layer_index.get(layer, [])
        return [self._entries[k] for k in keys if k in self._entries]

    def search(self, query: str) -> list[ContextIndexEntry]:
        """Search entries by key or content preview.

        Args:
            query: Search string.

        Returns:
            List of matching entries.
        """
        query_lower = query.lower()
        results: list[ContextIndexEntry] = []
        for entry in self._entries.values():
            if query_lower in entry.key.lower() or query_lower in entry.content_preview.lower():
                results.append(entry)
        return results

    def search_by_tags(self, tags: list[str]) -> list[ContextIndexEntry]:
        """Search entries by tags.

        Args:
            tags: Tags to match (any tag match is sufficient).

        Returns:
            List of entries with matching tags.
        """
        tag_set = set(tags)
        results: list[ContextIndexEntry] = []
        for entry in self._entries.values():
            if tag_set & set(entry.tags):
                results.append(entry)
        return results

    def remove(self, key: str) -> bool:
        """Remove an entry from the index.

        Args:
            key: The entry key to remove.

        Returns:
            True if removed, False if not found.
        """
        entry = self._entries.pop(key, None)
        if entry is None:
            return False
        if entry.layer in self._layer_index:
            try:
                self._layer_index[entry.layer].remove(key)
            except ValueError:
                pass
        return True

    def clear(self) -> None:
        """Clear all entries from the index."""
        self._entries.clear()
        self._layer_index = {layer: [] for layer in ContextLayer}

    @property
    def count(self) -> int:
        """Number of entries in the index."""
        return len(self._entries)
