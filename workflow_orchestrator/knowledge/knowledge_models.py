"""Knowledge models — data models for the deterministic knowledge system.

All models are simple dataclasses — no vector databases or embeddings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class KnowledgeCategory(Enum):
    """Categories of knowledge entries."""

    ARCHITECTURE_DECISION = "architecture_decision"
    RFC = "rfc"
    CODING_STANDARD = "coding_standard"
    TEMPLATE = "template"
    WORKFLOW_TEMPLATE = "workflow_template"
    PROMPT_TEMPLATE = "prompt_template"
    PROVIDER_DOCUMENTATION = "provider_documentation"
    FIX_HISTORY = "fix_history"
    COMMON_SOLUTION = "common_solution"
    ERROR_SIGNATURE = "error_signature"
    GENERAL = "general"


@dataclass
class KnowledgeEntry:
    """A single entry in the knowledge base.

    Attributes:
        entry_id: Unique entry identifier.
        title: Entry title.
        content: Entry content.
        category: Knowledge category.
        tags: Searchable tags.
        source: Source of the knowledge.
        version: Version string.
        created_at: ISO-8601 timestamp.
        updated_at: ISO-8601 timestamp.
        metadata: Additional metadata.
    """

    entry_id: str = ""
    title: str = ""
    content: str = ""
    category: KnowledgeCategory = KnowledgeCategory.GENERAL
    tags: list[str] = field(default_factory=list)
    source: str = ""
    version: str = "1.0.0"
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeIndexEntry:
    """An entry in the knowledge search index.

    Attributes:
        entry_id: References the KnowledgeEntry.
        title: Entry title.
        category: Knowledge category.
        tags: Entry tags.
        content_preview: First N chars of content.
        keywords: Extracted keywords.
    """

    entry_id: str
    title: str
    category: KnowledgeCategory
    tags: list[str] = field(default_factory=list)
    content_preview: str = ""
    keywords: list[str] = field(default_factory=list)


@dataclass
class SearchResult:
    """Result of a knowledge search.

    Attributes:
        entry_id: Matched entry ID.
        title: Entry title.
        category: Knowledge category.
        score: Match score (0.0 to 1.0).
        matched_terms: Terms that matched.
        content_preview: Preview of matched content.
    """

    entry_id: str
    title: str
    category: KnowledgeCategory
    score: float = 0.0
    matched_terms: list[str] = field(default_factory=list)
    content_preview: str = ""
