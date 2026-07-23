"""Knowledge system — deterministic knowledge storage and retrieval.

Supports:
- Architecture decisions, RFCs, Coding standards
- Templates, Workflow templates, Prompt templates
- Provider documentation, Fix history
- Common solutions, Error signatures
- Search indexes, Tagging, Categories, Metadata

No vector databases, no embeddings. Simple deterministic indexing only.
"""

from __future__ import annotations

__all__ = [
    "KnowledgeBase",
    "KnowledgeStore",
    "KnowledgeIndex",
    "KnowledgeSearch",
    "KnowledgeLoader",
    # Models
    "KnowledgeEntry",
    "KnowledgeIndexEntry",
    "SearchResult",
    "KnowledgeCategory",
]

from workflow_orchestrator.knowledge.knowledge_base import KnowledgeBase
from workflow_orchestrator.knowledge.knowledge_store import KnowledgeStore
from workflow_orchestrator.knowledge.knowledge_index import KnowledgeIndex
from workflow_orchestrator.knowledge.knowledge_search import KnowledgeSearch
from workflow_orchestrator.knowledge.knowledge_loader import KnowledgeLoader
from workflow_orchestrator.knowledge.knowledge_models import (
    KnowledgeEntry,
    KnowledgeIndexEntry,
    SearchResult,
    KnowledgeCategory,
)
