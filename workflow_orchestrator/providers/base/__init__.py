"""Base provider abstractions — abstract interfaces and shared functionality.

All provider adapters must implement ``IProvider``. The ``BaseProvider``
class provides common lifecycle tracking, health management, and metrics
collection shared by all provider implementations.
"""

from __future__ import annotations

from workflow_orchestrator.providers.base.base_provider import BaseProvider
from workflow_orchestrator.providers.base.provider_metrics import ProviderMetrics

__all__ = [
    "BaseProvider",
    "ProviderMetrics",
]
