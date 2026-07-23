"""Context Engine — deterministic layered context assembly.

The Context Engine prepares consistent information for providers and agents
using 8 deterministic layers:
1. Project Contract (immutable, never pruned)
2. Workflow State
3. Relevant Artifacts
4. Execution History
5. Relevant Knowledge
6. User Preferences
7. Recent Errors
8. Rolling Summary

Contains NO provider-specific logic.
Performs NO AI reasoning.
"""

from __future__ import annotations

__all__ = [
    "ContextEngine",
    "ContextBuilder",
    "ContextBudget",
    "ContextCompressor",
    "ContextLayers",
    "ContextIndex",
    "ContextSelector",
    "ContextSnapshotManager",
    "ContextCache",
    # Models
    "ContextAssembly",
    "ContextLayerContent",
    "ContextLayer",
    "BudgetPriority",
    "ContextSnapshot",
    "CompressorResult",
    "ContextIndexEntry",
    "ContextCacheEntry",
]

from workflow_orchestrator.context.context_engine import ContextEngine
from workflow_orchestrator.context.context_builder import ContextBuilder
from workflow_orchestrator.context.context_budget import ContextBudget
from workflow_orchestrator.context.context_compressor import ContextCompressor
from workflow_orchestrator.context.context_layers import ContextLayers
from workflow_orchestrator.context.context_index import ContextIndex
from workflow_orchestrator.context.context_selector import ContextSelector
from workflow_orchestrator.context.context_snapshot import ContextSnapshotManager
from workflow_orchestrator.context.context_cache import ContextCache
from workflow_orchestrator.context.context_models import (
    ContextAssembly,
    ContextLayerContent,
    ContextLayer,
    BudgetPriority,
    ContextSnapshot,
    CompressorResult,
    ContextIndexEntry,
    ContextCacheEntry,
)
