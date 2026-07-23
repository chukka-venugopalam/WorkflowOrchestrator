"""Provider configuration — re-exports for convenience.

ProviderConfig is defined in providers.__init__ to avoid circular imports.
This module re-exports it for a cleaner import path.
"""

from __future__ import annotations

from workflow_orchestrator.providers import ProviderConfig

__all__ = ["ProviderConfig"]
