"""Knowledge index — deterministic keyword-based search index.

No vector databases, no embeddings. Simple keyword indexing.
Supports: tagging, categories, metadata.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from workflow_orchestrator.knowledge.knowledge_models import (
    KnowledgeCategory,
    KnowledgeEntry,
    KnowledgeIndexEntry,
    SearchResult,
)

logger = logging.getLogger(__name__)


class KnowledgeIndex:
    """Deterministic keyword-based search index for knowledge entries.

    Builds an inverted index from keywords to entry IDs.
    Supports search by keyword, tag, and category.

    Usage:
        >>> index = KnowledgeIndex()
        >>> index.add_entry(entry)
        >>> results = index.search("python dependency injection")
    """

    def __init__(self) -> None:
        self._entries: dict[str, KnowledgeIndexEntry] = {}
        self._keyword_index: dict[str, set[str]] = {}  # keyword → set of entry_ids
        self._tag_index: dict[str, set[str]] = {}  # tag → set of entry_ids
        self._category_index: dict[KnowledgeCategory, set[str]] = {
            cat: set() for cat in KnowledgeCategory
        }

    def add_entry(self, entry: KnowledgeEntry) -> KnowledgeIndexEntry:
        """Add an entry to the index.

        Args:
            entry: The knowledge entry to index.

        Returns:
            The created KnowledgeIndexEntry.
        """
        keywords = self._extract_keywords(entry.title + " " + entry.content)
        index_entry = KnowledgeIndexEntry(
            entry_id=entry.entry_id,
            title=entry.title,
            category=entry.category,
            tags=list(entry.tags),
            content_preview=entry.content[:200],
            keywords=keywords,
        )
        self._entries[entry.entry_id] = index_entry

        # Index keywords
        for kw in keywords:
            if kw not in self._keyword_index:
                self._keyword_index[kw] = set()
            self._keyword_index[kw].add(entry.entry_id)

        # Index tags
        for tag in entry.tags:
            tag_lower = tag.lower()
            if tag_lower not in self._tag_index:
                self._tag_index[tag_lower] = set()
            self._tag_index[tag_lower].add(entry.entry_id)

        # Index category
        self._category_index[entry.category].add(entry.entry_id)

        return index_entry

    def remove_entry(self, entry_id: str) -> bool:
        """Remove an entry from the index.

        Args:
            entry_id: The entry to remove.

        Returns:
            True if removed.
        """
        entry = self._entries.pop(entry_id, None)
        if entry is None:
            return False

        # Remove from keyword index
        for kw in list(self._keyword_index.keys()):
            self._keyword_index[kw].discard(entry_id)
            if not self._keyword_index[kw]:
                del self._keyword_index[kw]

        # Remove from tag index
        for tag in entry.tags:
            tag_lower = tag.lower()
            if tag_lower in self._tag_index:
                self._tag_index[tag_lower].discard(entry_id)

        # Remove from category index
        self._category_index[entry.category].discard(entry_id)

        return True

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search for entries matching the query.

        Args:
            query: Search query string.
            limit: Maximum results.

        Returns:
            List of SearchResult objects, sorted by relevance.
        """
        query_terms = set(self._extract_keywords(query))
        if not query_terms:
            return []

        scored: dict[str, float] = {}
        matched_terms: dict[str, list[str]] = {}

        for term in query_terms:
            matching = self._keyword_index.get(term, set())
            for eid in matching:
                scored[eid] = scored.get(eid, 0) + 1.0
                if eid not in matched_terms:
                    matched_terms[eid] = []
                matched_terms[eid].append(term)

        # Sort by score descending
        sorted_results = sorted(scored.items(), key=lambda x: -x[1])

        results: list[SearchResult] = []
        for eid, score in sorted_results[:limit]:
            entry = self._entries.get(eid)
            if entry:
                max_possible = len(query_terms)
                normalized_score = score / max(max_possible, 1)
                results.append(SearchResult(
                    entry_id=eid,
                    title=entry.title,
                    category=entry.category,
                    score=normalized_score,
                    matched_terms=matched_terms.get(eid, []),
                    content_preview=entry.content_preview,
                ))

        return results

    def search_by_tag(self, tag: str) -> list[SearchResult]:
        """Search for entries by tag.

        Args:
            tag: The tag to search for.

        Returns:
            List of matching SearchResult objects.
        """
        tag_lower = tag.lower()
        matching = self._tag_index.get(tag_lower, set())
        return [
            SearchResult(
                entry_id=eid,
                title=self._entries[eid].title,
                category=self._entries[eid].category,
                score=1.0,
                matched_terms=[tag],
                content_preview=self._entries[eid].content_preview,
            )
            for eid in matching if eid in self._entries
        ]

    def search_by_category(self, category: KnowledgeCategory) -> list[SearchResult]:
        """Search for entries by category.

        Args:
            category: The category to filter by.

        Returns:
            List of matching SearchResult objects.
        """
        matching = self._category_index.get(category, set())
        return [
            SearchResult(
                entry_id=eid,
                title=self._entries[eid].title,
                category=category,
                score=1.0,
                content_preview=self._entries[eid].content_preview,
            )
            for eid in matching if eid in self._entries
        ]

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from text.

        Uses simple word-based tokenization.
        No NLP, no stemming, no embeddings.

        Args:
            text: Text to extract keywords from.

        Returns:
            List of lowercase keyword strings.
        """
        words = re.findall(r'[a-zA-Z][a-zA-Z0-9_-]{1,}', text.lower())
        # Filter common English stop words
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'can', 'shall',
            'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
            'as', 'into', 'through', 'during', 'before', 'after',
            'and', 'but', 'or', 'nor', 'not', 'so', 'yet', 'both',
            'either', 'neither', 'this', 'that', 'these', 'those',
            'it', 'its', 'it\'s', 'we', 'they', 'he', 'she', 'which',
            'who', 'whom', 'what', 'where', 'when', 'why', 'how',
        }
        return [w for w in words if w not in stop_words]

    @property
    def count(self) -> int:
        """Number of indexed entries."""
        return len(self._entries)
