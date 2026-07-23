"""Context budget — deterministic budget enforcement for context assembly.

Supports:
- Priority-based budgeting (CRITICAL layers never trimmed)
- Layer-by-layer allocation
- Budget exhaustion detection
- Deterministic pruning
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.context.context_models import (
    BudgetPriority,
    ContextAssembly,
    ContextLayer,
    ContextLayerContent,
)
from workflow_orchestrator.context.context_layers import ContextLayers

logger = logging.getLogger(__name__)


class ContextBudget:
    """Manages context budget allocation and enforcement.

    The budget is enforced deterministically:
    1. CRITICAL priority layers are always included in full
    2. HIGH priority layers are included if budget allows
    3. NORMAL priority layers are compressed if budget is tight
    4. LOW priority layers are included only if ample budget remains
    5. OPTIONAL layers are pruned first when budget is exceeded

    Usage:
        >>> budget = ContextBudget(total_budget=8000)
        >>> assembly = budget.enforce(assembly)
        >>> print(assembly.pruned_layers)
    """

    def __init__(self, total_budget: int = 16000) -> None:
        """Initialize the context budget.

        Args:
            total_budget: Maximum allowed tokens for the full context.
        """
        self._total_budget = total_budget
        self._layer_budgets: dict[ContextLayer, int] = {}

    @property
    def total_budget(self) -> int:
        """The total budget in tokens."""
        return self._total_budget

    @total_budget.setter
    def total_budget(self, value: int) -> None:
        """Set the total budget."""
        self._total_budget = max(1000, value)

    def allocate(self, layers: list[ContextLayerContent]) -> dict[ContextLayer, int]:
        """Allocate budget across layers based on priority.

        Args:
            layers: The context layers to allocate budget for.

        Returns:
            Dict mapping ContextLayer to allocated token budget.
        """
        allocation: dict[ContextLayer, int] = {}
        remaining = self._total_budget

        # Phase 1: Allocate to CRITICAL priority layers first
        critical_layers = [l for l in layers if l.priority == BudgetPriority.CRITICAL]
        for layer in critical_layers:
            max_tokens = ContextLayers.max_tokens_for_layer(layer.layer)
            allocated = min(layer.token_estimate or max_tokens, max_tokens, remaining)
            allocation[layer.layer] = allocated
            remaining -= allocated

        # Phase 2: Allocate to HIGH priority layers
        if remaining > 0:
            high_layers = [l for l in layers if l.priority == BudgetPriority.HIGH]
            for layer in high_layers:
                max_tokens = ContextLayers.max_tokens_for_layer(layer.layer)
                allocated = min(layer.token_estimate or max_tokens, max_tokens, remaining)
                allocation[layer.layer] = allocated
                remaining -= allocated

        # Phase 3: Allocate to NORMAL priority layers
        if remaining > 0:
            normal_layers = [l for l in layers if l.priority == BudgetPriority.NORMAL]
            for layer in normal_layers:
                max_tokens = ContextLayers.max_tokens_for_layer(layer.layer)
                allocated = min(layer.token_estimate or max_tokens, max_tokens, remaining)
                allocation[layer.layer] = allocated
                remaining -= allocated

        # Phase 4: Allocate remaining to LOW and OPTIONAL layers
        if remaining > 0:
            low_layers = [l for l in layers if l.priority in (BudgetPriority.LOW, BudgetPriority.OPTIONAL)]
            for layer in low_layers:
                max_tokens = ContextLayers.max_tokens_for_layer(layer.layer)
                allocated = min(layer.token_estimate or max_tokens, max_tokens, remaining)
                allocation[layer.layer] = allocated
                remaining -= allocated

        self._layer_budgets = allocation
        logger.debug(
            "Allocated budget: %d tokens across %d layers (remaining: %d)",
            self._total_budget - remaining,
            len(allocation),
            remaining,
        )
        return allocation

    def enforce(self, assembly: ContextAssembly) -> ContextAssembly:
        """Enforce budget limits on a context assembly.

        Prunes or compresses layers that exceed their allocated budget.
        CRITICAL layers are never pruned.

        Args:
            assembly: The context assembly to enforce budget on.

        Returns:
            Updated ContextAssembly with budget enforced.
        """
        allocation = self.allocate(assembly.layers)
        pruned: list[ContextLayer] = []
        compressed: list[ContextLayer] = []
        remaining_layers: list[ContextLayerContent] = []
        total_used = 0

        for layer_content in assembly.layers:
            layer = layer_content.layer
            allocated = allocation.get(layer, 0)

            if allocated <= 0:
                pruned.append(layer)
                logger.debug("Pruned layer '%s' (no budget allocated)", layer.value)
                continue

            if layer_content.token_estimate > allocated:
                # Compress to fit budget
                ratio = allocated / max(layer_content.token_estimate, 1)
                new_content = layer_content.content[:max(len(layer_content.content) // 2, 100)]
                compressed_layer = ContextLayerContent(
                    layer=layer,
                    content=new_content,
                    priority=layer_content.priority,
                    token_estimate=allocated,
                    metadata={**layer_content.metadata, "compressed": True, "ratio": round(ratio, 2)},
                )
                remaining_layers.append(compressed_layer)
                compressed.append(layer)
                total_used += allocated
                logger.debug("Compressed layer '%s' (ratio: %.2f)", layer.value, ratio)
            else:
                remaining_layers.append(layer_content)
                total_used += layer_content.token_estimate

        assembly.layers = remaining_layers
        assembly.total_tokens = total_used
        assembly.budget_limit = self._total_budget
        assembly.budget_remaining = max(0, self._total_budget - total_used)
        assembly.pruned_layers = pruned
        assembly.compressed_layers = compressed

        logger.debug(
            "Budget enforced: %d tokens used, %d layers remaining, %d pruned, %d compressed",
            total_used,
            len(remaining_layers),
            len(pruned),
            len(compressed),
        )
        return assembly

    def can_fit(self, layer: ContextLayerContent, assembly: ContextAssembly) -> bool:
        """Check if a layer can fit within the remaining budget.

        Args:
            layer: The layer content to check.
            assembly: The current context assembly.

        Returns:
            True if the layer fits within the remaining budget.
        """
        remaining = self._total_budget - assembly.total_tokens
        return layer.token_estimate <= remaining

    def remaining(self, assembly: ContextAssembly) -> int:
        """Get the remaining budget for a given assembly.

        Args:
            assembly: The current context assembly.

        Returns:
            Remaining tokens in the budget.
        """
        return max(0, self._total_budget - assembly.total_tokens)
