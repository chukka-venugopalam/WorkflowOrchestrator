"""Registry for AI provider adapters.

Manages registration, lifecycle, health tracking, and capability
discovery for all AI providers. No provider implementations exist
in this module — it only manages the registry layer.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.intelligence.models import (
    Capability,
    CostEstimate,
    ProviderHealth,
    ProviderManifest,
    ProviderStatus,
)
from workflow_orchestrator.intelligence.provider import IProvider

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry that manages available AI providers.

    Supports:
    - Register and unregister provider adapters
    - Look up providers by ID or capability
    - Track provider health status
    - Discover provider capabilities

    Usage:
        >>> registry = ProviderRegistry()
        >>> registry.register(provider_instance)
        >>> provider = registry.lookup("anthropic.claude")
        >>> health = registry.health("anthropic.claude")
        >>> providers_with_capability = registry.find_by_capability("reasoning.code-review")
    """

    def __init__(self) -> None:
        self._providers: dict[str, IProvider] = {}
        self._health_cache: dict[str, ProviderHealth] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, provider: IProvider, overwrite: bool = False) -> None:
        """Register a provider adapter.

        Args:
            provider: An IProvider implementation.
            overwrite: If True, replace an existing provider with the same ID.

        Raises:
            ValueError: If a provider with the same ID is already registered
                and ``overwrite`` is False.
        """
        manifest = provider.manifest()
        pid = manifest.id

        if pid in self._providers and not overwrite:
            raise ValueError(
                f"Provider '{pid}' is already registered. "
                "Use overwrite=True to replace."
            )

        self._providers[pid] = provider
        logger.info(
            "Registered provider '%s' (v%s) with %d capabilities",
            pid,
            manifest.version,
            len(manifest.capabilities),
        )

    def unregister(self, provider_id: str) -> bool:
        """Unregister a provider.

        Args:
            provider_id: The provider identifier.

        Returns:
            True if the provider was unregistered, False if not found.
        """
        if provider_id in self._providers:
            del self._providers[provider_id]
            self._health_cache.pop(provider_id, None)
            logger.info("Unregistered provider '%s'", provider_id)
            return True
        return False

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def lookup(self, provider_id: str) -> IProvider | None:
        """Look up a provider by ID.

        Args:
            provider_id: The provider identifier.

        Returns:
            The provider instance, or None if not found.
        """
        return self._providers.get(provider_id)

    def lookup_required(self, provider_id: str) -> IProvider:
        """Look up a provider by ID, raising if not found.

        Args:
            provider_id: The provider identifier.

        Returns:
            The provider instance.

        Raises:
            KeyError: If the provider is not registered.
        """
        provider = self.lookup(provider_id)
        if provider is None:
            raise KeyError(
                f"Provider '{provider_id}' is not registered. "
                f"Available: {list(self._providers.keys())}"
            )
        return provider

    def list_providers(self) -> list[IProvider]:
        """List all registered providers.

        Returns:
            List of all IProvider instances.
        """
        return list(self._providers.values())

    def list_ids(self) -> list[str]:
        """List all registered provider IDs.

        Returns:
            Sorted list of provider IDs.
        """
        return sorted(self._providers.keys())

    # ------------------------------------------------------------------
    # Capability-based discovery
    # ------------------------------------------------------------------

    def find_by_capability(self, capability_id: str) -> list[IProvider]:
        """Find providers that support a specific capability.

        Args:
            capability_id: The capability ID to search for.

        Returns:
            List of providers that declare support for this capability.
        """
        results: list[IProvider] = []
        for provider in self._providers.values():
            manifest = provider.manifest()
            for cap in manifest.capabilities:
                if cap.id == capability_id:
                    results.append(provider)
                    break
        return results

    def find_by_capabilities(
        self,
        capability_ids: list[str],
        require_all: bool = False,
    ) -> list[IProvider]:
        """Find providers that support one or more capabilities.

        Args:
            capability_ids: List of capability IDs to search for.
            require_all: If True, provider must support ALL capabilities.
                If False, provider must support at least one.

        Returns:
            List of matching providers.
        """
        if require_all:
            return [
                p for p in self._providers.values()
                if self._supports_all(p, capability_ids)
            ]
        return [
            p for p in self._providers.values()
            if self._supports_any(p, capability_ids)
        ]

    def _supports_all(self, provider: IProvider, cap_ids: list[str]) -> bool:
        """Check if a provider supports all given capabilities."""
        provider_caps = {c.id for c in provider.manifest().capabilities}
        return all(cid in provider_caps for cid in cap_ids)

    def _supports_any(self, provider: IProvider, cap_ids: list[str]) -> bool:
        """Check if a provider supports any of the given capabilities."""
        provider_caps = {c.id for c in provider.manifest().capabilities}
        return any(cid in provider_caps for cid in cap_ids)

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def health(self, provider_id: str) -> ProviderHealth | None:
        """Get the health status of a provider.

        Args:
            provider_id: The provider identifier.

        Returns:
            ProviderHealth, or None if the provider is not registered.
        """
        provider = self.lookup(provider_id)
        if provider is None:
            return None
        try:
            health = await provider.health()
            self._health_cache[provider_id] = health
            return health
        except Exception as exc:
            logger.warning("Health check failed for '%s': %s", provider_id, exc)
            return ProviderHealth(
                provider_id=provider_id,
                status=ProviderStatus.UNAVAILABLE,
                message=str(exc),
            )

    async def health_all(self) -> dict[str, ProviderHealth]:
        """Check health of all registered providers.

        Returns:
            Dict mapping provider ID to health status.
        """
        results: dict[str, ProviderHealth] = {}
        for pid in self._providers:
            health = await self.health(pid)
            if health:
                results[pid] = health
        return results

    def get_cached_health(self, provider_id: str) -> ProviderHealth | None:
        """Get the most recently cached health status.

        Args:
            provider_id: The provider identifier.

        Returns:
            Cached ProviderHealth, or None.
        """
        return self._health_cache.get(provider_id)

    def clear_health_cache(self) -> None:
        """Clear all cached health data."""
        self._health_cache.clear()

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def metadata(self, provider_id: str) -> ProviderManifest | None:
        """Get the manifest for a provider.

        Args:
            provider_id: The provider identifier.

        Returns:
            ProviderManifest, or None if not found.
        """
        provider = self.lookup(provider_id)
        if provider is None:
            return None
        return provider.manifest()

    def capabilities(self, provider_id: str) -> list[Capability]:
        """Get the capabilities of a specific provider.

        Args:
            provider_id: The provider identifier.

        Returns:
            List of Capability objects, or empty list if provider not found.
        """
        provider = self.lookup(provider_id)
        if provider is None:
            return []
        return provider.manifest().capabilities

    def all_capabilities(self) -> dict[str, list[Capability]]:
        """Get capabilities for all providers.

        Returns:
            Dict mapping provider ID to list of capabilities.
        """
        return {pid: p.manifest().capabilities for pid, p in self._providers.items()}

    # ------------------------------------------------------------------
    # Count
    # ------------------------------------------------------------------

    @property
    def count(self) -> int:
        """Number of registered providers."""
        return len(self._providers)
