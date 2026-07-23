"""Prompt Runtime — renders templates, injects context/artifacts, and versions prompts.

Coordinates with the Context Engine, Artifact Manager, and Knowledge Base
to assemble structured prompts ready for provider formatting.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from string import Template
from typing import Any, Optional

from workflow_orchestrator.intelligence.models import (
    ArtifactReference,
    ContextBundle,
    Prompt,
)

logger = logging.getLogger(__name__)


class PromptRuntime:
    """Runtime for prompt assembly, rendering, and versioning.

    Supports:
    - Template rendering with variable injection
    - Context injection from Context Engine
    - Artifact reference injection
    - Contract and knowledge injection
    - History injection
    - Prompt versioning

    Usage:
        >>> runtime = PromptRuntime()
        >>> prompt = runtime.render_goal("Build a login page", {
        ...     "project": "my-app",
        ...     "stack": "Next.js + Tailwind",
        ... })
        >>> result = runtime.inject_context(prompt, context_assembly)
    """

    def __init__(
        self,
        templates_dir: Path | str | None = None,
        max_history_entries: int = 10,
        event_bus: Any = None,
    ) -> None:
        """Initialize the Prompt Runtime.

        Args:
            templates_dir: Optional directory for prompt templates.
            max_history_entries: Maximum history entries to include.
            event_bus: Optional EventBus for publishing events.
        """
        self._templates_dir = Path(templates_dir) if templates_dir else None
        self._max_history_entries = max_history_entries
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # Template rendering
    # ------------------------------------------------------------------

    def render_goal(
        self,
        goal: str,
        variables: dict[str, Any] | None = None,
        template_name: str | None = None,
    ) -> str:
        """Render a goal string with variable injection.

        Supports Python string.Template syntax: ``$var`` and ``${var}``.

        Args:
            goal: The goal string with optional template variables.
            variables: Variables to inject.
            template_name: Optional template name (loads from templates dir).

        Returns:
            Rendered goal string.
        """
        if template_name and self._templates_dir:
            goal = self._load_template(template_name)

        if not variables:
            return goal

        return Template(goal).safe_substitute(**variables)

    def render_from_template(
        self,
        template_name: str,
        variables: dict[str, Any] | None = None,
    ) -> str:
        """Render a template file with variables.

        Args:
            template_name: Name of the template file.
            variables: Variables to inject.

        Returns:
            Rendered template string.

        Raises:
            FileNotFoundError: If the template is not found.
        """
        template_content = self._load_template(template_name)
        if not variables:
            return template_content
        return Template(template_content).safe_substitute(**variables)

    def _load_template(self, template_name: str) -> str:
        """Load a prompt template from disk.

        Args:
            template_name: Template name (with or without extension).

        Returns:
            Template content.

        Raises:
            FileNotFoundError: If the template is not found.
        """
        if self._templates_dir is None:
            raise FileNotFoundError("No templates directory configured")

        # Try with .txt extension first, then without
        template_path = self._templates_dir / template_name
        if not template_path.exists():
            template_path = self._templates_dir / f"{template_name}.txt"

        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_name}")

        return template_path.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Context injection
    # ------------------------------------------------------------------

    def inject_context(self, prompt: Prompt, context: ContextBundle | dict[str, Any] | None = None) -> Prompt:
        """Inject context into a prompt.

        Args:
            prompt: The prompt to inject context into.
            context: Context bundle or dict to inject.

        Returns:
            Updated Prompt with injected context.
        """
        if context is None:
            return prompt

        if isinstance(context, dict):
            # Dict format
            context_str = context.get("context", context.get("immutable_core", ""))
            if context_str:
                prompt.context = prompt.context + "\n\n" + context_str if prompt.context else context_str

            summary = context.get("summary", context.get("rolling_summary", ""))
            if summary:
                prompt.context = prompt.context + "\n\nProgress:\n" + summary if prompt.context else summary
        else:
            # ContextBundle format
            if context.immutable_core:
                prompt.context = prompt.context + "\n\n" + context.immutable_core if prompt.context else context.immutable_core
            if context.rolling_summary:
                prompt.context = prompt.context + "\n\nProgress:\n" + context.rolling_summary if prompt.context else context.rolling_summary

            # Add working set artifacts
            for ref in context.working_set:
                if ref not in prompt.artifacts:
                    prompt.artifacts.append(ref)

            # Add recent history
            for entry in context.recent_history:
                if entry not in prompt.history:
                    prompt.history.append(entry)

            # Add budget info
            prompt.budget["remaining"] = context.budget_remaining

        return prompt

    # ------------------------------------------------------------------
    # Artifact injection
    # ------------------------------------------------------------------

    def inject_artifacts(
        self,
        prompt: Prompt,
        artifacts: list[ArtifactReference],
    ) -> Prompt:
        """Inject artifact references into a prompt.

        Args:
            prompt: The prompt to inject artifacts into.
            artifacts: Artifact references to inject.

        Returns:
            Updated Prompt with artifact references.
        """
        for artifact in artifacts:
            if artifact not in prompt.artifacts:
                prompt.artifacts.append(artifact)
        return prompt

    # ------------------------------------------------------------------
    # Constraint injection
    # ------------------------------------------------------------------

    def inject_constraints(
        self,
        prompt: Prompt,
        constraints: list[str],
    ) -> Prompt:
        """Inject constraints into a prompt.

        Args:
            prompt: The prompt to inject constraints into.
            constraints: Constraints to inject.

        Returns:
            Updated Prompt with constraints.
        """
        for constraint in constraints:
            if constraint not in prompt.constraints:
                prompt.constraints.append(constraint)
        return prompt

    # ------------------------------------------------------------------
    # Knowledge injection
    # ------------------------------------------------------------------

    def inject_knowledge(
        self,
        prompt: Prompt,
        knowledge_content: str,
        knowledge_label: str = "Knowledge",
    ) -> Prompt:
        """Inject knowledge base content into a prompt's context.

        Args:
            prompt: The prompt to inject knowledge into.
            knowledge_content: Knowledge content to inject.
            knowledge_label: Label for the knowledge section.

        Returns:
            Updated Prompt with knowledge injected.
        """
        if knowledge_content:
            knowledge_section = f"\n\n=== {knowledge_label} ===\n{knowledge_content}"
            prompt.context = (prompt.context or "") + knowledge_section
        return prompt

    # ------------------------------------------------------------------
    # Contract injection
    # ------------------------------------------------------------------

    def inject_contract(
        self,
        prompt: Prompt,
        contract_summary: str,
    ) -> Prompt:
        """Inject project contract into a prompt.

        Args:
            prompt: The prompt to inject contract into.
            contract_summary: The contract summary.

        Returns:
            Updated Prompt with contract injected.
        """
        if contract_summary:
            contract_section = f"\n\n=== Project Contract ===\n{contract_summary}"
            prompt.context = (prompt.context or "") + contract_section
        return prompt

    # ------------------------------------------------------------------
    # History injection
    # ------------------------------------------------------------------

    def inject_history(
        self,
        prompt: Prompt,
        history_entries: list[dict[str, Any]],
    ) -> Prompt:
        """Inject conversation/execution history into a prompt.

        Args:
            prompt: The prompt to inject history into.
            history_entries: History entries to inject.

        Returns:
            Updated Prompt with history.
        """
        entries = history_entries[-self._max_history_entries:]
        for entry in entries:
            if entry not in prompt.history:
                prompt.history.append(entry)
        return prompt

    # ------------------------------------------------------------------
    # Build complete prompt
    # ------------------------------------------------------------------

    def build_prompt(
        self,
        goal: str,
        variables: dict[str, Any] | None = None,
        context: Any = None,
        artifacts: list[ArtifactReference] | None = None,
        constraints: list[str] | None = None,
        knowledge: str | None = None,
        contract: str | None = None,
        history: list[dict[str, Any]] | None = None,
        budget: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Prompt:
        """Build a complete prompt with all injections.

        Args:
            goal: The task goal.
            variables: Template variables for goal.
            context: Context bundle or dict.
            artifacts: Artifact references.
            constraints: Constraints.
            knowledge: Knowledge content.
            contract: Contract summary.
            history: History entries.
            budget: Budget info.
            metadata: Additional metadata.

        Returns:
            Complete Prompt ready for provider formatting.
        """
        # Render goal
        rendered_goal = self.render_goal(goal, variables)

        # Create base prompt
        prompt = Prompt(
            goal=rendered_goal,
            metadata=metadata or {},
        )

        # Inject context
        if context:
            prompt = self.inject_context(prompt, context)

        # Inject artifacts
        if artifacts:
            prompt = self.inject_artifacts(prompt, artifacts)

        # Inject constraints
        if constraints:
            prompt = self.inject_constraints(prompt, constraints)

        # Inject knowledge
        if knowledge:
            prompt = self.inject_knowledge(prompt, knowledge)

        # Inject contract
        if contract:
            prompt = self.inject_contract(prompt, contract)

        # Inject history
        if history:
            prompt = self.inject_history(prompt, history)

        # Inject budget
        if budget:
            prompt.budget.update(budget)

        # Add versioning metadata
        prompt.metadata["prompt_version"] = "1.0.0"
        prompt.metadata["generated_at"] = datetime.now(timezone.utc).isoformat()

        # Publish prompt.generated event
        self._publish_event("prompt.generated", {
            "goal": goal[:100],
            "artifact_count": len(prompt.artifacts),
            "constraint_count": len(prompt.constraints),
            "history_count": len(prompt.history),
            "has_context": bool(context),
            "has_knowledge": bool(knowledge),
            "has_contract": bool(contract),
        })

        logger.debug(
            "Built prompt: goal=%d chars, %d artifacts, %d constraints, %d history entries",
            len(prompt.goal),
            len(prompt.artifacts),
            len(prompt.constraints),
            len(prompt.history),
        )
        return prompt

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish a prompt event if an event bus is available.

        Args:
            event_type: The event type string.
            data: Event payload.
        """
        if self._event_bus is None:
            return
        try:
            from workflow_orchestrator.core.event_bus import Event
            self._event_bus.publish(Event(type=event_type, data=data, source="prompt_runtime"))
        except Exception:
            pass
