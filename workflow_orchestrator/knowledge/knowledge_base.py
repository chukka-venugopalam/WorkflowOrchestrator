"""Knowledge base — main interface for knowledge management.

Coordinates store, index, and search for deterministic knowledge access.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.knowledge.knowledge_index import KnowledgeIndex
from workflow_orchestrator.knowledge.knowledge_loader import KnowledgeLoader
from workflow_orchestrator.knowledge.knowledge_models import (
    KnowledgeCategory,
    KnowledgeEntry,
    SearchResult,
)
from workflow_orchestrator.knowledge.knowledge_search import KnowledgeSearch
from workflow_orchestrator.knowledge.knowledge_store import KnowledgeStore

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Main interface for the deterministic knowledge system.

    Coordinates storage, indexing, and search of knowledge entries.
    All operations are deterministic — no AI or embeddings.

    Usage:
        >>> kb = KnowledgeBase()
        >>> entry = kb.add("Python Best Practices", "Content...", KnowledgeCategory.CODING_STANDARD)
        >>> results = kb.search("python best practices")
    """

    def __init__(
        self,
        store: KnowledgeStore | None = None,
        index: KnowledgeIndex | None = None,
        loader: KnowledgeLoader | None = None,
    ) -> None:
        self._store = store or KnowledgeStore()
        self._index = index or KnowledgeIndex()
        self._search = KnowledgeSearch(self._index)
        self._loader = loader or KnowledgeLoader()

        # Index existing entries on startup
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        """Rebuild the search index from stored entries."""
        for entry in self._store.list_all():
            self._index.add_entry(entry)

    @property
    def store(self) -> KnowledgeStore:
        """The underlying knowledge store."""
        return self._store

    @property
    def index(self) -> KnowledgeIndex:
        """The search index."""
        return self._index

    @property
    def search(self) -> KnowledgeSearch:
        """The search interface."""
        return self._search

    def add(
        self,
        title: str,
        content: str,
        category: KnowledgeCategory = KnowledgeCategory.GENERAL,
        tags: list[str] | None = None,
        source: str = "",
    ) -> KnowledgeEntry:
        """Add a new knowledge entry.

        Args:
            title: Entry title.
            content: Entry content.
            category: Knowledge category.
            tags: Optional tags.
            source: Source description.

        Returns:
            The created KnowledgeEntry.
        """
        entry = self._store.create(
            title=title,
            content=content,
            category=category,
            tags=tags,
            source=source,
        )
        self._index.add_entry(entry)
        return entry

    def get(self, entry_id: str) -> KnowledgeEntry | None:
        """Get a knowledge entry by ID.

        Args:
            entry_id: The entry identifier.

        Returns:
            The entry, or None.
        """
        return self._store.get(entry_id)

    def search(
        self,
        query: str,
        category: KnowledgeCategory | None = None,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """Search knowledge entries.

        Args:
            query: Search query.
            category: Optional category filter.
            limit: Maximum results.
            min_score: Minimum relevance score.

        Returns:
            List of SearchResult objects.
        """
        return self._search.search(query, category=category, limit=limit, min_score=min_score)
