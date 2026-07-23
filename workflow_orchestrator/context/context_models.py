"""Context models — data models for the Context Engine.

All models are deterministic and provider-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ContextLayer(Enum):
    """Context layers ordered by priority (highest = never pruned first)."""

    PROJECT_CONTRACT = "project_contract"
    WORKFLOW_STATE = "workflow_state"
    RELEVANT_ARTIFACTS = "relevant_artifacts"
    EXECUTION_HISTORY = "execution_history"
    RELEVANT_KNOWLEDGE = "relevant_knowledge"
    USER_PREFERENCES = "user_preferences"
    RECENT_ERRORS = "recent_errors"
    ROLLING_SUMMARY = "rolling_summary"


class BudgetPriority(Enum):
    """Priority for budget allocation (CRITICAL = never trimmed)."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    OPTIONAL = 4


@dataclass(frozen=True)
class ContextLayerContent:
    """Content for a single context layer.

    Attributes:
        layer: Which layer this content belongs to.
        content: The text content.
        priority: Budget priority.
        token_estimate: Estimated token count.
        metadata: Layer metadata.
    """

    layer: ContextLayer
    content: str = ""
    priority: BudgetPriority = BudgetPriority.NORMAL
    token_estimate: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextAssembly:
    """Assembled context with all layers and budget metadata.

    Attributes:
        layers: Ordered list of context layer content.
        total_tokens: Estimated total token count.
        budget_limit: Maximum allowed tokens.
        budget_remaining: Remaining budget after assembly.
        pruned_layers: Layers that were pruned due to budget.
        compressed_layers: Layers that were compressed.
        assembly_id: Unique assembly identifier.
        created_at: ISO-8601 timestamp.
    """

    layers: list[ContextLayerContent] = field(default_factory=list)
    total_tokens: int = 0
    budget_limit: int = 0
    budget_remaining: int = 0
    pruned_layers: list[ContextLayer] = field(default_factory=list)
    compressed_layers: list[ContextLayer] = field(default_factory=list)
    assembly_id: str = ""
    created_at: str = ""


@dataclass
class ContextSnapshot:
    """A snapshot of context at a point in time.

    Supports deterministic context reuse.

    Attributes:
        snapshot_id: Unique snapshot identifier.
        assembly: The assembled context.
        workflow_id: Associated workflow ID.
        step_index: Step index at time of snapshot.
        created_at: ISO-8601 timestamp.
        metadata: Additional metadata.
    """

    snapshot_id: str = ""
    assembly: ContextAssembly | None = None
    workflow_id: str = ""
    step_index: int = 0
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CompressorResult:
    """Result of compressing a context layer.

    Attributes:
        original_content: The original content before compression.
        compressed_content: The compressed content.
        original_tokens: Original token count.
        compressed_tokens: Compressed token count.
        compression_ratio: Ratio (0.0 to 1.0, higher = more compressed).
        method: Compression method used.
    """

    original_content: str = ""
    compressed_content: str = ""
    original_tokens: int = 0
    compressed_tokens: int = 0
    compression_ratio: float = 0.0
    method: str = "truncation"


@dataclass
class ContextIndexEntry:
    """An entry in the context index for fast lookups.

    Attributes:
        key: Lookup key.
        layer: Which layer the content belongs to.
        content_preview: First N chars of content.
        token_count: Estimated token count.
        created_at: ISO-8601 timestamp.
        tags: Categorization tags.
    """

    key: str
    layer: ContextLayer
    content_preview: str = ""
    token_count: int = 0
    created_at: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class ContextCacheEntry:
    """A cached context assembly.

    Attributes:
        cache_key: Unique cache key.
        assembly: The cached context assembly.
        hit_count: Number of cache hits.
        created_at: ISO-8601 timestamp.
        expires_at: ISO-8601 expiration timestamp.
    """

    cache_key: str = ""
    assembly: ContextAssembly | None = None
    hit_count: int = 0
    created_at: str = ""
    expires_at: str = ""
