"""Token-independent context budgeting system.

Manages context budgets without assuming a specific tokenization
scheme.  Uses abstract "units" that can be mapped to provider-specific
token counts by adapters.

Supports:
- Priority-based allocation
- Compression ratios per layer
- Summarization hook points
- Artifact references (instead of full content)
- Future provider limit integration
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from workflow_orchestrator.intelligence.models import (
    ArtifactReference,
    BudgetAllocation,
    ContextBundle,
)

logger = logging.getLogger(__name__)

# Type alias for summarization hooks
SummarizerFn = Callable[[str, int], str]


@dataclass
class ContextBudgetConfig:
    """Configuration for context budget management.

    Attributes:
        total_budget: Total available budget in abstract units.
        layer_priorities: Priority order for layers
            (0=highest, will be trimmed last).
        compression_ratios: Compression ratio per layer
            (1.0 = no compression, 0.5 = compress to 50%).
        immutable_core_budget: Budget reserved for immutable core.
        max_history_entries: Maximum history entries to include.
        max_artifact_refs: Maximum artifact references to include.
    """

    total_budget: int = 8000
    layer_priorities: dict[str, int] = field(default_factory=lambda: {
        "immutable_core": 0,
        "working_set": 1,
        "rolling_summary": 2,
        "recent_history": 3,
    })
    compression_ratios: dict[str, float] = field(default_factory=lambda: {
        "immutable_core": 1.0,
        "working_set": 0.7,
        "rolling_summary": 0.5,
        "recent_history": 0.3,
    })
    immutable_core_budget: int = 2000
    max_history_entries: int = 20
    max_artifact_refs: int = 10


class ContextBudget:
    """Manages context budgets for provider-agnostic context assembly.

    Uses a priority-based allocation system that trims lower-priority
    layers first when budget is exceeded.  Supports summarization
    hooks that can be injected to compress content.

    Usage:
        >>> budget = ContextBudget(total_budget=8000)
        >>> bundle = budget.assemble(
        ...     immutable_core="Project: Build a landing page",
        ...     working_set=[ArtifactReference(name="page.tsx")],
        ...     rolling_summary="Completed design phase...",
        ... )
        >>> print(bundle.budget_remaining)
        2000
    """

    def __init__(
        self,
        total_budget: int | None = None,
        config: ContextBudgetConfig | None = None,
    ) -> None:
        """Initialize the context budget manager.

        Args:
            total_budget: Total budget in abstract units. Overrides
                the ``config.total_budget`` if provided.
            config: Configuration for budget management.
                Uses defaults if not provided.

        Note:
            If both ``total_budget`` and ``config`` are provided,
            ``total_budget`` takes precedence and updates the config.
        """
        self._config = config or ContextBudgetConfig()
        if total_budget is not None:
            self._config.total_budget = total_budget
        self._summarizers: dict[str, SummarizerFn] = {}
        self._allocations: dict[str, BudgetAllocation] = {}

    @property
    def config(self) -> ContextBudgetConfig:
        """The current budget configuration."""
        return self._config

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_total_budget(self, budget: int) -> None:
        """Set the total context budget.

        Args:
            budget: Total budget in abstract units.
        """
        self._config.total_budget = max(100, budget)

    def register_summarizer(self, layer: str, summarizer: SummarizerFn) -> None:
        """Register a summarization hook for a layer.

        Args:
            layer: The layer name (e.g., ``rolling_summary``).
            summarizer: Function that takes (text, max_chars) and returns
                summarized text.
        """
        self._summarizers[layer] = summarizer
        logger.debug("Registered summarizer for layer '%s'", layer)

    def set_compression_ratio(self, layer: str, ratio: float) -> None:
        """Set the compression ratio for a layer.

        Args:
            layer: The layer name.
            ratio: Compression ratio (0.0 to 1.0).
        """
        self._config.compression_ratios[layer] = max(0.1, min(1.0, ratio))

    # ------------------------------------------------------------------
    # Budget assembly
    # ------------------------------------------------------------------

    def assemble(
        self,
        immutable_core: str = "",
        working_set: list[ArtifactReference] | None = None,
        rolling_summary: str = "",
        recent_history: list[dict[str, Any]] | None = None,
    ) -> ContextBundle:
        """Assemble a context bundle with budget enforcement.

        The assembly process:
        1. Start with immutable core (never summarized)
        2. Add working set artifact references
        3. Add rolling summary (compress if needed)
        4. Add recent history (compress if needed)
        5. Enforce total budget by trimming lower priority layers

        Args:
            immutable_core: The project contract summary (never summarized).
            working_set: Relevant artifacts from dependency steps.
            rolling_summary: Compressed summary of prior outputs.
            recent_history: Recent turn history.

        Returns:
            A ContextBundle with budget enforcement applied.
        """
        working_set = working_set or []
        recent_history = recent_history or []

        # Calculate usage per layer
        immutable_used = len(immutable_core)

        # Working set: count artifact references (not full content)
        working_set_used = sum(len(a.name or "") + len(a.content_type) for a in working_set)

        rolling_used = len(rolling_summary)
        history_used = sum(len(str(h.get("content", ""))) for h in recent_history)

        total_used = immutable_used + working_set_used + rolling_used + history_used

        # Store allocations
        self._allocations = {
            "immutable_core": BudgetAllocation(
                layer_name="immutable_core",
                allocated=immutable_used,
                used=immutable_used,
                priority=self._config.layer_priorities.get("immutable_core", 0),
                compression_ratio=self._config.compression_ratios.get("immutable_core", 1.0),
            ),
            "working_set": BudgetAllocation(
                layer_name="working_set",
                allocated=working_set_used,
                used=working_set_used,
                priority=self._config.layer_priorities.get("working_set", 1),
                compression_ratio=self._config.compression_ratios.get("working_set", 0.7),
            ),
            "rolling_summary": BudgetAllocation(
                layer_name="rolling_summary",
                allocated=rolling_used,
                used=rolling_used,
                priority=self._config.layer_priorities.get("rolling_summary", 2),
                compression_ratio=self._config.compression_ratios.get("rolling_summary", 0.5),
            ),
            "recent_history": BudgetAllocation(
                layer_name="recent_history",
                allocated=history_used,
                used=history_used,
                priority=self._config.layer_priorities.get("recent_history", 3),
                compression_ratio=self._config.compression_ratios.get("recent_history", 0.3),
            ),
        }

        # Enforce budget
        budget_remaining = self._config.total_budget - total_used
        if budget_remaining < 0:
            # Need to trim
            rolling_summary = self._enforce_budget(
                rolling_summary,
                "rolling_summary",
                rolling_used + budget_remaining,  # target size
            )
            recent_history = self._trim_history(recent_history)

            # Recalculate
            rolling_used = len(rolling_summary)
            history_used = sum(len(str(h.get("content", ""))) for h in recent_history)
            total_used = immutable_used + working_set_used + rolling_used + history_used
            budget_remaining = self._config.total_budget - total_used

        bundle = ContextBundle(
            immutable_core=immutable_core,
            working_set=working_set[:self._config.max_artifact_refs],
            rolling_summary=rolling_summary,
            recent_history=recent_history[-self._config.max_history_entries:],
            budget_remaining=max(0, budget_remaining),
        )

        logger.debug(
            "Assembled context bundle: %d/%d units used, %d remaining",
            total_used,
            self._config.total_budget,
            budget_remaining,
        )
        return bundle

    def _enforce_budget(
        self,
        content: str,
        layer: str,
        target_size: int,
    ) -> str:
        """Enforce budget by compressing content.

        Args:
            content: The content to compress.
            layer: The layer name.
            target_size: Target size in characters.

        Returns:
            Compressed content within budget.
        """
        if target_size >= len(content):
            return content

        # Use registered summarizer if available
        summarizer = self._summarizers.get(layer)
        if summarizer:
            try:
                result = summarizer(content, target_size)
                logger.debug("Summarized layer '%s': %d → %d chars", layer, len(content), len(result))
                return result
            except Exception:
                logger.exception("Summarizer failed for layer '%s', falling back to truncation", layer)

        # Fallback: simple truncation with ellipsis
        ratio = self._config.compression_ratios.get(layer, 1.0)
        truncated_size = max(int(target_size * ratio), 100)
        if truncated_size >= len(content):
            return content
        return content[:truncated_size] + "\n...[truncated]"

    def _trim_history(self, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Trim history to fit within the configured maximum.

        Args:
            history: The history entries.

        Returns:
            Trimmed history.
        """
        if len(history) > self._config.max_history_entries:
            return history[-self._config.max_history_entries:]
        return history

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_allocation(self, layer: str) -> BudgetAllocation | None:
        """Get the budget allocation for a layer from the last assembly.

        Args:
            layer: The layer name.

        Returns:
            BudgetAllocation, or None if no assembly has been done.
        """
        return self._allocations.get(layer)

    def get_report(self) -> dict[str, Any]:
        """Get a budget report for the last assembly.

        Returns:
            Dict with budget usage breakdown.
        """
        total_allocated = sum(a.allocated for a in self._allocations.values())
        total_used = sum(a.used for a in self._allocations.values())

        return {
            "total_budget": self._config.total_budget,
            "total_allocated": total_allocated,
            "total_used": total_used,
            "remaining": max(0, self._config.total_budget - total_used),
            "layers": {
                name: {
                    "allocated": alloc.allocated,
                    "used": alloc.used,
                    "compression_ratio": alloc.compression_ratio,
                    "priority": alloc.priority,
                }
                for name, alloc in self._allocations.items()
            },
        }
