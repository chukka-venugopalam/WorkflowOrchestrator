"""Provider registry runtime — manages provider lifecycle, health, and discovery.

Extends the base ProviderRegistry with lifecycle management:
- Initialize/connect all registered providers
- Health monitoring and status aggregation
- Provider discovery and capability indexing
- Event publishing for provider lifecycle events
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from workflow_orchestrator.intelligence.models import (
    Capability,
    ProviderHealth,
    ProviderManifest,
    ProviderStatus,
)
from workflow_orchestrator.intelligence.provider import IProvider
from workflow_orchestrator.intelligence.provider_registry import ProviderRegistry

logger = logging.getLogger(__name__)


class ProviderRegistryRuntime:
    """Runtime manager for provider lifecycle and health.

    Wraps the ProviderRegistry with lifecycle management, health
    monitoring, and capability indexing.

    Usage:
        >>> runtime = ProviderRegistryRuntime(registry)
        >>> await runtime.initialize_all()
        >>> health = await runtime.check_health("anthropic.claude")
        >>> await runtime.shutdown_all()
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        event_bus: Any = None,
        capability_registry: Any = None,
    ) -> None:
        """Initialize the provider registry runtime.

        Args:
            registry: The underlying ProviderRegistry.
            event_bus: Optional EventBus for publishing events.
            capability_registry: Optional CapabilityRegistry for capability indexing.
        """
        self._registry = registry
        self._event_bus = event_bus
        self._capability_registry = capability_registry
        self._health_cache: dict[str, ProviderHealth] = {}
        self._initialized: bool = False

    @property
    def registry(self) -> ProviderRegistry:
        """The underlying provider registry."""
        return self._registry

    @property
    def initialized(self) -> bool:
        """Whether all providers have been initialized."""
        return self._initialized

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------

    async def initialize_all(self) -> dict[str, bool]:
        """Initialize all registered providers.

        Returns:
            Dict mapping provider ID to initialization success.
        """
        results: dict[str, bool] = {}
        for provider in self._registry.list_providers():
            try:
                await provider.initialize()
                results[provider.provider_id] = True
                self._index_capabilities(provider)
                self._publish_event("provider.initialized", {
                    "provider_id": provider.provider_id,
                    "name": provider.provider_name,
                })
            except Exception as exc:
                logger.error("Failed to initialize provider '%s': %s", provider.provider_id, exc)
                results[provider.provider_id] = False
                self._publish_event("provider.initialization_failed", {
                    "provider_id": provider.provider_id,
                    "error": str(exc),
                })

        self._initialized = True
        logger.info("Provider initialization complete: %d/%d succeeded",
                     sum(1 for v in results.values() if v), len(results))
        return results

    async def shutdown_all(self) -> None:
        """Shut down all registered providers gracefully."""
        for provider in self._registry.list_providers():
            try:
                await provider.shutdown()
                self._publish_event("provider.shutdown", {
                    "provider_id": provider.provider_id,
                })
            except Exception as exc:
                logger.warning("Error shutting down provider '%s': %s", provider.provider_id, exc)

        self._initialized = False
        self._health_cache.clear()
        logger.info("All providers shut down")

    # ------------------------------------------------------------------
    # Health monitoring
    # ------------------------------------------------------------------

    async def check_health(self, provider_id: str) -> ProviderHealth | None:
        """Check the health of a specific provider.

        Args:
            provider_id: The provider identifier.

        Returns:
            ProviderHealth status, or None if provider not found.
        """
        provider = self._registry.lookup(provider_id)
        if provider is None:
            return None

        try:
            health = await provider.health()
            self._health_cache[provider_id] = health
            return health
        except Exception as exc:
            health = ProviderHealth(
                provider_id=provider_id,
                status=ProviderStatus.UNAVAILABLE,
                message=str(exc),
            )
            self._health_cache[provider_id] = health
            return health

    async def check_all_health(self) -> dict[str, ProviderHealth]:
        """Check health of all registered providers.

        Returns:
            Dict mapping provider ID to health status.
        """
        results: dict[str, ProviderHealth] = {}
        for pid in self._registry.list_ids():
            health = await self.check_health(pid)
            if health:
                results[pid] = health
        return results

    def get_cached_health(self, provider_id: str) -> ProviderHealth | None:
        """Get cached health for a provider.

        Args:
            provider_id: The provider identifier.

        Returns:
            Cached health status, or None.
        """
        return self._health_cache.get(provider_id)

    def get_available_providers(self) -> list[IProvider]:
        """Get providers that are currently available (healthy).

        Returns:
            List of available providers.
        """
        available: list[IProvider] = []
        for provider in self._registry.list_providers():
            cached = self._health_cache.get(provider.provider_id)
            if cached and cached.status == ProviderStatus.AVAILABLE:
                available.append(provider)
            elif not cached:
                # Not yet checked — include anyway (optimistic)
                available.append(provider)
        return available

    # ------------------------------------------------------------------
    # Capability indexing
    # ------------------------------------------------------------------

    def _index_capabilities(self, provider: IProvider) -> None:
        """Index a provider's capabilities into the CapabilityRegistry.

        Args:
            provider: The provider to index.
        """
        if self._capability_registry is None:
            return

        manifest = provider.manifest()
        for cap in manifest.capabilities:
            from workflow_orchestrator.core.capability_registry import (
                CapabilityManifest,
                CandidateHealth,
                CostTier,
                QualityLevel,
            )
            try:
                self._capability_registry.register(CapabilityManifest(
                    id=cap.id,
                    name=cap.id,
                    description=cap.description,
                    provider_id=manifest.id,
                    version=manifest.version,
                    cost_tier=CostTier.MEDIUM,
                    quality=QualityLevel.STABLE,
                    health=CandidateHealth.AVAILABLE,
                    metadata={"provider_name": manifest.name},
                ))
            except Exception as exc:
                logger.warning("Failed to index capability '%s': %s", cap.id, exc)

    # ------------------------------------------------------------------
    # Provider operations
    # ------------------------------------------------------------------

    async def execute(
        self,
        provider_id: str,
        request: Any,
    ) -> Any:
        """Execute a request through a specific provider.

        Args:
            provider_id: The provider identifier.
            request: The execution request.

        Returns:
            The execution result.

        Raises:
            KeyError: If the provider is not registered.
        """
        provider = self._registry.lookup_required(provider_id)
        return await provider.submit(request)

    async def connect(self, provider_id: str) -> bool:
        """Connect to a provider (initialize if needed).

        Args:
            provider_id: The provider identifier.

        Returns:
            True if connected successfully.
        """
        provider = self._registry.lookup(provider_id)
        if provider is None:
            return False
        try:
            await provider.initialize()
            self._publish_event("provider.connected", {"provider_id": provider_id})
            return True
        except Exception:
            return False

    async def disconnect(self, provider_id: str) -> bool:
        """Disconnect from a provider.

        Args:
            provider_id: The provider identifier.

        Returns:
            True if disconnected successfully.
        """
        provider = self._registry.lookup(provider_id)
        if provider is None:
            return False
        try:
            await provider.shutdown()
            self._publish_event("provider.disconnected", {"provider_id": provider_id})
            return True
        except Exception:
            return False

    def status(self, provider_id: str) -> ProviderStatus:
        """Get the status of a provider.

        Args:
            provider_id: The provider identifier.

        Returns:
            Current provider status.
        """
        provider = self._registry.lookup(provider_id)
        if provider is None:
            return ProviderStatus.UNINITIALIZED
        return provider.status if hasattr(provider, "status") else ProviderStatus.UNINITIALIZED

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_metrics(self, provider_id: str) -> dict[str, Any] | None:
        """Get metrics for a provider.

        Args:
            provider_id: The provider identifier.

        Returns:
            Provider metrics dict, or None.
        """
        provider = self._registry.lookup(provider_id)
        if provider is None:
            return None
        if hasattr(provider, "metrics"):
            return provider.metrics.to_dict()  # type: ignore[union-attr]
        return None

    def get_all_metrics(self) -> dict[str, dict[str, Any]]:
        """Get metrics for all providers.

        Returns:
            Dict mapping provider ID to metrics.
        """
        results: dict[str, dict[str, Any]] = {}
        for pid in self._registry.list_ids():
            metrics = self.get_metrics(pid)
            if metrics:
                results[pid] = metrics
        return results

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if the event bus is available.

        Args:
            event_type: The event type string.
            data: Event payload.
        """
        if self._event_bus is None:
            return
        try:
            from workflow_orchestrator.core.event_bus import Event
            self._event_bus.publish(Event(type=event_type, data=data, source="provider_registry_runtime"))
        except Exception:
            pass
