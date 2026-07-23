"""Context layers — layered context assembly for the Context Engine.

Supports 8 layers of context, from most critical to least:
1. Project Contract (never pruned)
2. Workflow State
3. Relevant Artifacts
4. Execution History
5. Relevant Knowledge
6. User Preferences
7. Recent Errors
8. Rolling Summary
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.context.context_models import (
    BudgetPriority,
    ContextLayer,
    ContextLayerContent,
)

logger = logging.getLogger(__name__)


class ContextLayers:
    """Manages layered context assembly for the Context Engine.

    Provides factory methods for creating context layers with
    appropriate priorities and metadata.

    Usage:
        >>> layers = ContextLayers()
        >>> contract_layer = layers.contract("Project contract...")
        >>> state_layer = layers.workflow_state({"status": "running"})
    """

    # Layer configuration: (layer, priority, max_tokens)
    LAYER_CONFIG: list[tuple[ContextLayer, BudgetPriority, int]] = [
        (ContextLayer.PROJECT_CONTRACT, BudgetPriority.CRITICAL, 4000),
        (ContextLayer.WORKFLOW_STATE, BudgetPriority.CRITICAL, 2000),
        (ContextLayer.RELEVANT_ARTIFACTS, BudgetPriority.HIGH, 8000),
        (ContextLayer.EXECUTION_HISTORY, BudgetPriority.HIGH, 4000),
        (ContextLayer.RELEVANT_KNOWLEDGE, BudgetPriority.NORMAL, 4000),
        (ContextLayer.USER_PREFERENCES, BudgetPriority.NORMAL, 1000),
        (ContextLayer.RECENT_ERRORS, BudgetPriority.LOW, 2000),
        (ContextLayer.ROLLING_SUMMARY, BudgetPriority.LOW, 2000),
    ]

    @staticmethod
    def contract(content: str = "", metadata: dict[str, Any] | None = None) -> ContextLayerContent:
        """Create a project contract layer (highest priority).

        Args:
            content: Contract summary content.
            metadata: Layer metadata.

        Returns:
            A ContextLayerContent for the contract layer.
        """
        return ContextLayerContent(
            layer=ContextLayer.PROJECT_CONTRACT,
            content=content,
            priority=BudgetPriority.CRITICAL,
            token_estimate=len(content) // 4,
            metadata=metadata or {},
        )

    @staticmethod
    def workflow_state(
        state: dict[str, Any] | str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ContextLayerContent:
        """Create a workflow state layer.

        Args:
            state: Workflow state dict or string representation.
            metadata: Layer metadata.

        Returns:
            A ContextLayerContent for the workflow state layer.
        """
        content = str(state) if isinstance(state, dict) else state
        return ContextLayerContent(
            layer=ContextLayer.WORKFLOW_STATE,
            content=content,
            priority=BudgetPriority.CRITICAL,
            token_estimate=len(content) // 4,
            metadata=metadata or {},
        )

    @staticmethod
    def artifacts(
        content: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ContextLayerContent:
        """Create a relevant artifacts layer.

        Args:
            content: Artifact descriptions or references.
            metadata: Layer metadata.

        Returns:
            A ContextLayerContent for the artifacts layer.
        """
        return ContextLayerContent(
            layer=ContextLayer.RELEVANT_ARTIFACTS,
            content=content,
            priority=BudgetPriority.HIGH,
            token_estimate=len(content) // 4,
            metadata=metadata or {},
        )

    @staticmethod
    def history(
        content: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ContextLayerContent:
        """Create an execution history layer.

        Args:
            content: Execution history text.
            metadata: Layer metadata.

        Returns:
            A ContextLayerContent for the execution history layer.
        """
        return ContextLayerContent(
            layer=ContextLayer.EXECUTION_HISTORY,
            content=content,
            priority=BudgetPriority.HIGH,
            token_estimate=len(content) // 4,
            metadata=metadata or {},
        )

    @staticmethod
    def knowledge(
        content: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ContextLayerContent:
        """Create a relevant knowledge layer.

        Args:
            content: Knowledge base content.
            metadata: Layer metadata.

        Returns:
            A ContextLayerContent for the knowledge layer.
        """
        return ContextLayerContent(
            layer=ContextLayer.RELEVANT_KNOWLEDGE,
            content=content,
            priority=BudgetPriority.NORMAL,
            token_estimate=len(content) // 4,
            metadata=metadata or {},
        )

    @staticmethod
    def preferences(
        content: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ContextLayerContent:
        """Create a user preferences layer.

        Args:
            content: User preference descriptions.
            metadata: Layer metadata.

        Returns:
            A ContextLayerContent for the user preferences layer.
        """
        return ContextLayerContent(
            layer=ContextLayer.USER_PREFERENCES,
            content=content,
            priority=BudgetPriority.NORMAL,
            token_estimate=len(content) // 4,
            metadata=metadata or {},
        )

    @staticmethod
    def errors(
        content: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ContextLayerContent:
        """Create a recent errors layer.

        Args:
            content: Error descriptions.
            metadata: Layer metadata.

        Returns:
            A ContextLayerContent for the errors layer.
        """
        return ContextLayerContent(
            layer=ContextLayer.RECENT_ERRORS,
            content=content,
            priority=BudgetPriority.LOW,
            token_estimate=len(content) // 4,
            metadata=metadata or {},
        )

    @staticmethod
    def summary(
        content: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ContextLayerContent:
        """Create a rolling summary layer (lowest priority).

        Args:
            content: Summary of prior steps.
            metadata: Layer metadata.

        Returns:
            A ContextLayerContent for the summary layer.
        """
        return ContextLayerContent(
            layer=ContextLayer.ROLLING_SUMMARY,
            content=content,
            priority=BudgetPriority.OPTIONAL,
            token_estimate=len(content) // 4,
            metadata=metadata or {},
        )

    @staticmethod
    def estimate_tokens(content: str) -> int:
        """Rough token estimation (~4 chars per token).

        Args:
            content: Text content.

        Returns:
            Estimated token count.
        """
        return len(content) // 4

    @staticmethod
    def layer_order() -> list[ContextLayer]:
        """Get layers in priority order (highest first).

        Returns:
            List of ContextLayer enums ordered by priority.
        """
        return [layer for layer, _, _ in ContextLayers.LAYER_CONFIG]

    @staticmethod
    def max_tokens_for_layer(layer: ContextLayer) -> int:
        """Get the maximum tokens for a specific layer.

        Args:
            layer: The context layer.

        Returns:
            Maximum token limit for the layer.
        """
        for l, _, max_tokens in ContextLayers.LAYER_CONFIG:
            if l == layer:
                return max_tokens
        return 2000

    @staticmethod
    def priority_for_layer(layer: ContextLayer) -> BudgetPriority:
        """Get the budget priority for a specific layer.

        Args:
            layer: The context layer.

        Returns:
            BudgetPriority for the layer.
        """
        for l, p, _ in ContextLayers.LAYER_CONFIG:
            if l == layer:
                return p
        return BudgetPriority.NORMAL
