"""Context Engine — orchestrates deterministic context assembly.

The Context Engine assembles layered context from multiple sources:
1. Project Contract (immutable, never pruned)
2. Workflow State
3. Relevant Artifacts
4. Execution History
5. Relevant Knowledge
6. User Preferences
7. Recent Errors
8. Rolling Summary

It enforces budgets, supports caching, and provides snapshots.
No AI reasoning is performed.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from workflow_orchestrator.context.context_budget import ContextBudget
from workflow_orchestrator.context.context_builder import ContextBuilder
from workflow_orchestrator.context.context_cache import ContextCache
from workflow_orchestrator.context.context_compressor import ContextCompressor
from workflow_orchestrator.context.context_index import ContextIndex
from workflow_orchestrator.context.context_layers import ContextLayers
from workflow_orchestrator.context.context_models import (
    ContextAssembly,
    ContextLayer,
    ContextLayerContent,
    ContextSnapshot,
)
from workflow_orchestrator.context.context_selector import ContextSelector
from workflow_orchestrator.context.context_snapshot import ContextSnapshotManager

logger = logging.getLogger(__name__)


class ContextEngine:
    """Orchestrates deterministic context assembly from multiple sources.

    The Context Engine is the single entry point for building,
    budgeting, caching, and snapshotting context.

    Usage:
        >>> engine = ContextEngine()
        >>> assembly = engine.assemble(
        ...     contract="Project summary...",
        ...     state={"status": "running"},
        ...     artifacts=[{"name": "build.log", "summary": "Build succeeded"}],
        ...     budget_limit=8000,
        ... )
        >>> print(len(assembly.layers))
    """

    def __init__(
        self,
        builder: ContextBuilder | None = None,
        budget: ContextBudget | None = None,
        compressor: ContextCompressor | None = None,
        cache: ContextCache | None = None,
        snapshot_manager: ContextSnapshotManager | None = None,
        index: ContextIndex | None = None,
        selector: ContextSelector | None = None,
    ) -> None:
        """Initialize the Context Engine with its components."""
        self._builder = builder or ContextBuilder()
        self._budget = budget or ContextBudget()
        self._compressor = compressor or ContextCompressor()
        self._cache = cache or ContextCache()
        self._snapshot_manager = snapshot_manager or ContextSnapshotManager()
        self._index = index or ContextIndex()
        self._selector = selector or ContextSelector(index=self._index)

    @property
    def budget(self) -> ContextBudget:
        """The budget manager."""
        return self._budget

    @property
    def cache(self) -> ContextCache:
        """The context cache."""
        return self._cache

    @property
    def snapshot_manager(self) -> ContextSnapshotManager:
        """The snapshot manager."""
        return self._snapshot_manager

    @property
    def index(self) -> ContextIndex:
        """The context index."""
        return self._index

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------

    def assemble(
        self,
        contract: str = "",
        state: dict[str, Any] | None = None,
        artifacts: list[dict[str, Any]] | None = None,
        execution_history: str = "",
        knowledge: str = "",
        preferences: str = "",
        errors: list[dict[str, Any]] | None = None,
        summary: str = "",
        budget_limit: int = 16000,
        use_cache: bool = True,
    ) -> ContextAssembly:
        """Assemble context from all available sources.

        Steps:
        1. Check cache (if enabled)
        2. Build context layers
        3. Apply budget enforcement
        4. Cache result
        5. Index content

        Args:
            contract: Project contract summary.
            state: Current workflow state.
            artifacts: Relevant artifacts.
            execution_history: Execution history.
            knowledge: Knowledge base content.
            preferences: User preferences.
            errors: Recent errors.
            summary: Rolling summary.
            budget_limit: Maximum budget in tokens.
            use_cache: Whether to check cache first.

        Returns:
            A ContextAssembly with all layers and budget metadata.
        """
        # Check cache
        if use_cache:
            cache_inputs = {
                "contract": contract,
                "state": str(state),
                "artifact_count": len(artifacts or []),
                "history_len": len(execution_history),
                "knowledge": knowledge,
                "preferences": preferences,
                "error_count": len(errors or []),
                "summary": summary,
                "budget": budget_limit,
            }
            cache_key = self._cache.make_key(cache_inputs)
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Returning cached context assembly (key: %s)", cache_key[:8])
                return cached

        # Build layers
        layers = self._builder.build_all(
            contract=contract,
            state=state,
            artifacts=artifacts,
            execution_history=execution_history,
            knowledge=knowledge,
            preferences=preferences,
            errors=errors,
            summary=summary,
        )

        # Create assembly
        assembly_id = uuid.uuid4().hex[:12]
        total_tokens = sum(l.token_estimate for l in layers)
        assembly = ContextAssembly(
            layers=layers,
            total_tokens=total_tokens,
            budget_limit=budget_limit,
            assembly_id=assembly_id,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Apply budget
        self._budget.total_budget = budget_limit
        assembly = self._budget.enforce(assembly)

        # Cache the result
        if use_cache:
            self._cache.put(cache_key, assembly)

        # Index content
        for layer in assembly.layers:
            if layer.content:
                self._index.index(
                    key=f"{assembly_id}:{layer.layer.value}",
                    layer=layer.layer,
                    content=layer.content,
                    tags=[layer.layer.value, "context_assembly"],
                )

        logger.debug(
            "Assembled context: %d layers, %d tokens (budget: %d)",
            len(assembly.layers),
            assembly.total_tokens,
            budget_limit,
        )
        return assembly

    # ------------------------------------------------------------------
    # Budget management
    # ------------------------------------------------------------------

    def with_budget(self, budget_limit: int) -> ContextEngine:
        """Create a new engine with a different budget limit.

        Args:
            budget_limit: Maximum allowed tokens.

        Returns:
            A new ContextEngine with the updated budget.
        """
        engine = ContextEngine(
            builder=self._builder,
            compressor=self._compressor,
            cache=self._cache,
            snapshot_manager=self._snapshot_manager,
            index=self._index,
            selector=self._selector,
        )
        engine._budget = ContextBudget(total_budget=budget_limit)
        return engine

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def snapshot(
        self,
        assembly: ContextAssembly,
        workflow_id: str = "",
        step_index: int = 0,
    ) -> ContextSnapshot:
        """Create a snapshot of the current context.

        Args:
            assembly: The context assembly to snapshot.
            workflow_id: Associated workflow ID.
            step_index: Current step index.

        Returns:
            The created ContextSnapshot.
        """
        return self._snapshot_manager.create(
            assembly=assembly,
            workflow_id=workflow_id,
            step_index=step_index,
        )

    def restore(self, snapshot_id: str) -> ContextAssembly | None:
        """Restore a context assembly from a snapshot.

        Args:
            snapshot_id: The snapshot identifier.

        Returns:
            The restored ContextAssembly, or None.
        """
        return self._snapshot_manager.load_assembly(snapshot_id)

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def select_for_step(self, step_capability: str, keys: list[str] | None = None) -> list[ContextLayerContent]:
        """Select context layers relevant to a workflow step.

        Args:
            step_capability: The step's capability ID.
            keys: Available context keys.

        Returns:
            Relevant context layer content.
        """
        return self._selector.select_for_step(step_capability, keys)

    def select_for_error(self, error_type: str, error_message: str) -> list[ContextLayerContent]:
        """Select context layers relevant to error recovery.

        Args:
            error_type: The error type.
            error_message: The error message.

        Returns:
            Relevant context layer content.
        """
        return self._selector.select_for_error(error_type, error_message)

    # ------------------------------------------------------------------
    # Context to bundle conversion
    # ------------------------------------------------------------------

    def to_bundle(self, assembly: ContextAssembly) -> dict[str, Any]:
        """Convert a context assembly to a provider-agnostic bundle.

        Args:
            assembly: The context assembly.

        Returns:
            Dict with bundle-ready context.
        """
        layers_by_name: dict[str, str] = {}
        for layer in assembly.layers:
            layers_by_name[layer.layer.value] = layer.content

        return {
            "immutable_core": layers_by_name.get("project_contract", ""),
            "workflow_state": layers_by_name.get("workflow_state", ""),
            "working_set": layers_by_name.get("relevant_artifacts", ""),
            "rolling_summary": layers_by_name.get("rolling_summary", ""),
            "execution_history": layers_by_name.get("execution_history", ""),
            "relevant_knowledge": layers_by_name.get("relevant_knowledge", ""),
            "user_preferences": layers_by_name.get("user_preferences", ""),
            "recent_errors": layers_by_name.get("recent_errors", ""),
            "total_tokens": assembly.total_tokens,
            "budget_remaining": assembly.budget_remaining,
            "pruned_layers": [l.value for l in assembly.pruned_layers],
            "compressed_layers": [l.value for l in assembly.compressed_layers],
        }
