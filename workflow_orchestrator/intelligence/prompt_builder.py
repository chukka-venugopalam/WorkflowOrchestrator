"""Reusable prompt assembly system.

Assembles structured prompts from components:
goal, context, artifacts, constraints, history, budget.

No provider formatting yet — produces a provider-agnostic Prompt
object that each provider adapter formats into its own convention.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.intelligence.models import (
    ArtifactReference,
    ContextBundle,
    Prompt,
)

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Assembles structured prompts from components.

    The builder produces a provider-agnostic ``Prompt`` object.
    Each provider adapter is responsible for formatting this into
    its own request format.

    Usage:
        >>> builder = PromptBuilder()
        >>> prompt = builder.build(
        ...     goal="Build a login page",
        ...     context="Project uses Next.js with Tailwind",
        ...     artifacts=[ArtifactReference(name="design.png")],
        ...     constraints=["Use TypeScript"],
        ...     history=[{"role": "user", "content": "..."}],
        ...     budget={"remaining_tokens": 4000},
        ... )
        >>> print(prompt.goal)
        'Build a login page'
    """

    def __init__(self, max_artifact_summaries: int = 5) -> None:
        """Initialize the prompt builder.

        Args:
            max_artifact_summaries: Maximum number of artifact references
                to include in a single prompt.
        """
        self._max_artifact_summaries = max_artifact_summaries

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(
        self,
        goal: str = "",
        context: str = "",
        artifacts: list[ArtifactReference] | None = None,
        constraints: list[str] | None = None,
        history: list[dict[str, Any]] | None = None,
        budget: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Prompt:
        """Build a structured prompt from components.

        Args:
            goal: The primary objective or task description.
            context: Contextual information (project, tech stack, etc.).
            artifacts: Artifacts to reference in the prompt.
            constraints: Explicit constraints (e.g., "Use TypeScript").
            history: Prior conversation or execution history.
            budget: Context budget summary.
            metadata: Additional prompt metadata.

        Returns:
            A structured Prompt object ready for provider formatting.
        """
        # Validate and normalize
        goal = goal.strip()
        context = context.strip()

        # Limit artifact references
        artifacts = artifacts or []
        if len(artifacts) > self._max_artifact_summaries:
            artifacts = artifacts[:self._max_artifact_summaries]

        prompt = Prompt(
            goal=goal,
            context=context,
            artifacts=artifacts,
            constraints=constraints or [],
            history=history or [],
            budget=budget or {},
            metadata=metadata or {},
        )

        logger.debug(
            "Built prompt: goal=%d chars, context=%d chars, %d artifacts, %d constraints, %d history entries",
            len(goal),
            len(context),
            len(artifacts),
            len(prompt.constraints),
            len(prompt.history),
        )
        return prompt

    # ------------------------------------------------------------------
    # Component helpers
    # ------------------------------------------------------------------

    def build_from_bundle(
        self,
        bundle: ContextBundle,
        goal: str = "",
        constraints: list[str] | None = None,
    ) -> Prompt:
        """Build a prompt from a ContextBundle (Context Engine output).

        The ContextBundle contains pre-assembled layers that map
        directly to prompt components.

        Args:
            bundle: The ContextBundle from the Context Engine.
            goal: Optional overriding goal.
            constraints: Optional additional constraints.

        Returns:
            A structured Prompt.
        """
        # Assemble context from bundle layers
        context_parts = []

        if bundle.immutable_core:
            context_parts.append(f"=== Project Contract ===\n{bundle.immutable_core}")

        if bundle.working_set:
            working_set_summary = "\n".join(
                f"- {a.name} ({a.content_type})" for a in bundle.working_set
            )
            context_parts.append(f"=== Working Set ===\n{working_set_summary}")

        if bundle.rolling_summary:
            context_parts.append(f"=== Progress Summary ===\n{bundle.rolling_summary}")

        assembled_context = "\n\n".join(context_parts)

        return self.build(
            goal=goal,
            context=assembled_context,
            artifacts=bundle.working_set,
            constraints=constraints or [],
            history=bundle.recent_history,
            budget={"remaining": bundle.budget_remaining},
        )

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render_plain_text(self, prompt: Prompt) -> str:
        """Render a prompt as plain text.

        This is a simple rendering suitable for debugging or as a
        fallback. Provider adapters should implement their own
        formatting for optimal results.

        Args:
            prompt: The prompt to render.

        Returns:
            Plain text representation of the prompt.
        """
        parts: list[str] = []

        if prompt.goal:
            parts.append(f"# Goal\n{prompt.goal}\n")

        if prompt.constraints:
            parts.append("# Constraints\n" + "\n".join(f"- {c}" for c in prompt.constraints) + "\n")

        if prompt.context:
            parts.append(f"# Context\n{prompt.context}\n")

        if prompt.artifacts:
            parts.append("# Artifacts\n" + "\n".join(
                f"- {a.name} ({a.content_type})" for a in prompt.artifacts
            ) + "\n")

        if prompt.budget:
            parts.append(f"# Budget\n{prompt.budget}\n")

        if prompt.history:
            parts.append(f"# History ({len(prompt.history)} entries)")

        return "\n".join(parts)

    def render_structurally(self, prompt: Prompt) -> dict[str, Any]:
        """Render a prompt as a structured dictionary.

        Each component is mapped to a named section for provider
        adapters to format according to their own conventions.

        Args:
            prompt: The prompt to render.

        Returns:
            Dict with named sections: goal, context, artifacts, etc.
        """
        return {
            "objective": prompt.goal,
            "context": prompt.context,
            "constraints": prompt.constraints,
            "artifacts": [
                {
                    "name": a.name,
                    "content_type": a.content_type,
                    "hash": a.hash,
                    "uri": a.uri,
                }
                for a in prompt.artifacts
            ],
            "conversation_history": [
                {"role": entry.get("role", "user"), "content": str(entry.get("content", ""))}
                for entry in prompt.history
            ],
            "budget": {
                "remaining": prompt.budget.get("remaining", 0),
                "total": prompt.budget.get("total", 0),
            },
        }

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    @property
    def max_artifact_summaries(self) -> int:
        """Maximum number of artifact summaries to include."""
        return self._max_artifact_summaries

    @max_artifact_summaries.setter
    def max_artifact_summaries(self, value: int) -> None:
        """Set the maximum number of artifact summaries."""
        self._max_artifact_summaries = max(1, value)
