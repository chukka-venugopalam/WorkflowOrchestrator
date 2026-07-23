"""Knowledge search — search interface with deterministic ranking.

Combines keyword, tag, and category search with scoring.
No AI, no embeddings, no vector databases.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.knowledge.knowledge_index import KnowledgeIndex
from workflow_orchestrator.knowledge.knowledge_models import (
    KnowledgeCategory,
    SearchResult,
)

logger = logging.getLogger(__name__)


class KnowledgeSearch:
    """Search interface for the knowledge base.

    Supports:
    - Full-text keyword search
    - Tag-based search
    - Category filtering
    - Combined queries

    Usage:
        >>> search = KnowledgeSearch(index)
        >>> results = search.search("python dependency injection")
        >>> results = search.search_by_category(KnowledgeCategory.ARCHITECTURE_DECISION)
    """

    def __init__(self, index: KnowledgeIndex) -> None:
        self._index = index

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
            min_score: Minimum relevance score (0.0 to 1.0).

        Returns:
            List of SearchResult objects.
        """
        results = self._index.search(query, limit=limit * 2)

        if category is not None:
            results = [r for r in results if r.category == category]

        results = [r for r in results if r.score >= min_score]

        return results[:limit]

    def search_by_tags(
        self,
        tags: list[str],
        require_all: bool = False,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search by tags.

        Args:
            tags: Tags to search for.
            require_all: If True, match all tags. If False, match any.
            limit: Maximum results.

        Returns:
            List of SearchResult objects.
        """
        if not tags:
            return []

        if require_all:
            # Intersection: entries with ALL tags
            tag_sets: list[set[str]] = []
            for tag in tags:
                results = self._index.search_by_tag(tag)
                tag_sets.append({r.entry_id for r in results})

            if tag_sets:
                common = tag_sets[0]
                for ts in tag_sets[1:]:
                    common &= ts
                matching = common
            else:
                matching = set()
        else:
            # Union: entries with ANY tag
            matching: set[str] = set()
            for tag in tags:
                results = self._index.search_by_tag(tag)
                matching.update(r.entry_id for r in results)

        all_results = []
        for tag in tags:
            all_results.extend(self._index.search_by_tag(tag))

        seen: set[str] = set()
        results: list[SearchResult] = []
        for r in all_results:
            if r.entry_id in matching and r.entry_id not in seen:
                seen.add(r.entry_id)
                results.append(r)

        return results[:limit]

    def search_by_category(
        self,
        category: KnowledgeCategory,
        query: str = "",
    ) -> list[SearchResult]:
        """Search entries within a category.

        Args:
            category: Category to search within.
            query: Optional additional filter.

        Returns:
            List of SearchResult objects.
        """
        if query:
            return self.search(query, category=category)

        return self._index.search_by_category(category)
