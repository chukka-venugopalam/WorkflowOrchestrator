"""Context builder — assembles context from multiple data sources.

The ContextBuilder collects content from:
- Project Contract
- Workflow State Engine
- Artifact Manager
- Execution History
- Knowledge Base
- User Preferences
- Error Logs
- Session Manager

No AI reasoning is performed — assembly is deterministic.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.context.context_layers import ContextLayers
from workflow_orchestrator.context.context_models import (
    ContextAssembly,
    ContextLayer,
    ContextLayerContent,
)

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Builds context content from available data sources.

    Collects and organizes content from various sources into
    context layer content objects ready for assembly.

    Usage:
        >>> builder = ContextBuilder()
        >>> layers = builder.build_all(
        ...     contract="Project contract...",
        ...     state={"status": "running"},
        ...     artifacts=[{"id": "art-1", "summary": "Build output"}],
        ... )
        >>> print(len(layers))
        8
    """

    def build_all(
        self,
        contract: str = "",
        state: dict[str, Any] | None = None,
        artifacts: list[dict[str, Any]] | None = None,
        execution_history: str = "",
        knowledge: str = "",
        preferences: str = "",
        errors: list[dict[str, Any]] | None = None,
        summary: str = "",
    ) -> list[ContextLayerContent]:
        """Build all context layers from available sources.

        Args:
            contract: Project contract summary.
            state: Current workflow state.
            artifacts: List of relevant artifacts.
            execution_history: Execution history text.
            knowledge: Relevant knowledge base content.
            preferences: User preferences.
            errors: Recent error entries.
            summary: Rolling summary of prior steps.

        Returns:
            Ordered list of ContextLayerContent, highest priority first.
        """
        layers: list[ContextLayerContent] = []

        # Layer 1: Project Contract (never pruned)
        if contract:
            layers.append(ContextLayers.contract(contract))

        # Layer 2: Workflow State
        if state:
            content = self._format_state(state)
            layers.append(ContextLayers.workflow_state(content))

        # Layer 3: Relevant Artifacts
        if artifacts:
            content = self._format_artifacts(artifacts)
            layers.append(ContextLayers.artifacts(content))

        # Layer 4: Execution History
        if execution_history:
            layers.append(ContextLayers.history(execution_history))

        # Layer 5: Relevant Knowledge
        if knowledge:
            layers.append(ContextLayers.knowledge(knowledge))

        # Layer 6: User Preferences
        if preferences:
            layers.append(ContextLayers.preferences(preferences))

        # Layer 7: Recent Errors
        if errors:
            content = self._format_errors(errors)
            layers.append(ContextLayers.errors(content))

        # Layer 8: Rolling Summary
        if summary:
            layers.append(ContextLayers.summary(summary))

        return layers

    def _format_state(self, state: dict[str, Any]) -> str:
        """Format workflow state as a string.

        Args:
            state: Workflow state dict.

        Returns:
            Formatted state string.
        """
        parts = []
        for key, value in state.items():
            parts.append(f"{key}: {value}")
        return "\n".join(parts)

    def _format_artifacts(self, artifacts: list[dict[str, Any]]) -> str:
        """Format artifacts as a string.

        Args:
            artifacts: List of artifact dicts.

        Returns:
            Formatted artifact descriptions.
        """
        lines = []
        for art in artifacts:
            name = art.get("name", art.get("id", "unknown"))
            summary = art.get("summary", art.get("description", ""))
            if summary:
                lines.append(f"- {name}: {summary}")
            else:
                lines.append(f"- {name}")
        return "\n".join(lines)

    def _format_errors(self, errors: list[dict[str, Any]]) -> str:
        """Format errors as a string.

        Args:
            errors: List of error dicts.

        Returns:
            Formatted error descriptions.
        """
        lines = []
        for error in errors:
            msg = error.get("message", error.get("error", str(error)))
            err_type = error.get("type", "error")
            lines.append(f"[{err_type}] {msg[:200]}")
        return "\n".join(lines)
