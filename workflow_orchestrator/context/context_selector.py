"""Context selector — selects relevant context content for a given use case.

Deterministically selects context content based on:
- Workflow step requirements
- Capability requirements
- Error context
- Phase changes
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.context.context_index import ContextIndex
from workflow_orchestrator.context.context_layers import ContextLayers
from workflow_orchestrator.context.context_models import (
    ContextLayer,
    ContextLayerContent,
)

logger = logging.getLogger(__name__)


class ContextSelector:
    """Selects relevant context content based on the current need.

    Usage:
        >>> selector = ContextSelector(index)
        >>> layers = selector.select_for_step("verify.build", ["build_output.log"])
    """

    def __init__(self, index: ContextIndex | None = None) -> None:
        """Initialize the context selector.

        Args:
            index: Optional context index for fast lookups.
        """
        self._index = index or ContextIndex()

    def select_for_step(
        self,
        step_capability: str,
        available_keys: list[str] | None = None,
    ) -> list[ContextLayerContent]:
        """Select context layers relevant to a workflow step.

        Args:
            step_capability: The capability ID of the step.
            available_keys: Keys of available context content.

        Returns:
            List of relevant ContextLayerContent objects.
        """
        layers: list[ContextLayerContent] = []

        # Always include workflow state (critical)
        layers.append(ContextLayers.workflow_state())

        # Include execution history if available
        if available_keys:
            history_content = self._collect_content(available_keys)
            if history_content:
                layers.append(ContextLayers.history(history_content))

        # Select artifacts based on capability
        if "verify" in step_capability or "deploy" in step_capability:
            if self._index:
                artifacts = self._index.lookup_by_layer(ContextLayer.RELEVANT_ARTIFACTS)
                if artifacts:
                    content = "\n".join(a.content_preview for a in artifacts[:5])
                    if content:
                        layers.append(ContextLayers.artifacts(content))

        return layers

    def select_for_error(self, error_type: str, error_message: str) -> list[ContextLayerContent]:
        """Select context layers relevant to error recovery.

        Args:
            error_type: The error type (e.g., "timeout", "build_failure").
            error_message: The error message.

        Returns:
            List of relevant ContextLayerContent objects.
        """
        layers: list[ContextLayerContent] = []

        # Include errors layer
        layers.append(ContextLayers.errors(f"Error [{error_type}]: {error_message}"))

        # Include workflow state for context
        layers.append(ContextLayers.workflow_state())

        # Include relevant knowledge if indexed
        if self._index:
            known_errors = self._index.search(error_type)
            if known_errors:
                content = "\n".join(e.content_preview for e in known_errors[:3])
                if content:
                    layers.append(ContextLayers.knowledge(f"Related patterns:\n{content}"))

        return layers

    def select_for_phase_change(self, phase_name: str) -> list[ContextLayerContent]:
        """Select context for a project phase transition.

        Args:
            phase_name: The target phase name.

        Returns:
            List of relevant ContextLayerContent objects.
        """
        layers: list[ContextLayerContent] = []

        layers.append(ContextLayers.contract(f"Transitioning to phase: {phase_name}"))
        layers.append(ContextLayers.workflow_state({"phase": phase_name}))

        # Include relevant knowledge for the phase
        if self._index:
            phase_entries = self._index.search(phase_name)
            if phase_entries:
                content = "\n".join(e.content_preview for e in phase_entries[:3])
                if content:
                    layers.append(ContextLayers.knowledge(content))

        return layers

    def _collect_content(self, keys: list[str]) -> str:
        """Collect content from the index by keys.

        Args:
            keys: Keys to look up.

        Returns:
            Concatenated content string.
        """
        parts: list[str] = []
        for key in keys:
            if self._index:
                entry = self._index.lookup(key)
                if entry:
                    parts.append(entry.content_preview)
        return "\n".join(parts)
