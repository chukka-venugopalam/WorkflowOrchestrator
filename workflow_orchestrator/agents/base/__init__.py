"""Base agent abstractions — abstract interfaces and shared functionality.

All agent adapters must implement ``IAgent``. The ``BaseAgent``
class provides common lifecycle tracking and workspace management.
"""

from __future__ import annotations

from workflow_orchestrator.agents.base.base_agent import BaseAgent

__all__ = [
    "BaseAgent",
]
