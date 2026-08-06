"""Provider registry — manages provider lifecycle, health, and discovery.

The ProviderRegistryRuntime wraps the base ProviderRegistry with lifecycle
management, health monitoring, and capability indexing.
"""

from __future__ import annotations

from workflow_orchestrator.providers.registry.provider_registry_runtime import ProviderRegistryRuntime

__all__ = [
    "ProviderRegistryRuntime",
]
