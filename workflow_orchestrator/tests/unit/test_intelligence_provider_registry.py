"""Unit tests for the ProviderRegistry."""

from __future__ import annotations

import pytest
from workflow_orchestrator.intelligence.provider_registry import ProviderRegistry
from workflow_orchestrator.intelligence.models import (
    Capability,
    CostEstimate,
    ExecutionRequest,
    ExecutionResult,
    ProviderHealth,
    ProviderManifest,
    ProviderStatus,
)
from tests.fixtures.intelligence_mocks import MockProvider


class TestProviderRegistry:
    def setup_method(self) -> None:
        self.registry = ProviderRegistry()
        self.provider1 = MockProvider("provider.a", ["cap.a", "cap.b"])
        self.provider2 = MockProvider("provider.b", ["cap.b", "cap.c"])

    def test_register_and_lookup(self) -> None:
        self.registry.register(self.provider1)
        assert self.registry.lookup("provider.a") is self.provider1

    def test_register_duplicate_raises(self) -> None:
        self.registry.register(self.provider1)
        with pytest.raises(ValueError, match="already registered"):
            self.registry.register(self.provider1)

    def test_register_overwrite(self) -> None:
        self.registry.register(self.provider1)
        new_provider = MockProvider("provider.a", ["cap.z"])
        self.registry.register(new_provider, overwrite=True)
        assert self.registry.lookup("provider.a") is new_provider

    def test_unregister(self) -> None:
        self.registry.register(self.provider1)
        assert self.registry.unregister("provider.a")
        assert self.registry.lookup("provider.a") is None

    def test_unregister_nonexistent(self) -> None:
        assert not self.registry.unregister("nonexistent")

    def test_lookup_required_found(self) -> None:
        self.registry.register(self.provider1)
        assert self.registry.lookup_required("provider.a") is self.provider1

    def test_lookup_required_not_found(self) -> None:
        with pytest.raises(KeyError):
            self.registry.lookup_required("nonexistent")

    def test_list_providers(self) -> None:
        self.registry.register(self.provider1)
        self.registry.register(self.provider2)
        assert len(self.registry.list_providers()) == 2

    def test_list_ids(self) -> None:
        self.registry.register(self.provider2)
        self.registry.register(self.provider1)
        assert self.registry.list_ids() == ["provider.a", "provider.b"]

    def test_find_by_capability(self) -> None:
        self.registry.register(self.provider1)
        self.registry.register(self.provider2)
        results = self.registry.find_by_capability("cap.a")
        assert len(results) == 1
        assert results[0].manifest().id == "provider.a"

        results = self.registry.find_by_capability("cap.b")
        assert len(results) == 2

        results = self.registry.find_by_capability("nonexistent")
        assert len(results) == 0

    def test_find_by_capabilities_any(self) -> None:
        self.registry.register(self.provider1)
        self.registry.register(self.provider2)
        results = self.registry.find_by_capabilities(["cap.a"])
        assert len(results) == 1

    def test_find_by_capabilities_all(self) -> None:
        self.registry.register(self.provider1)
        self.registry.register(self.provider2)
        results = self.registry.find_by_capabilities(["cap.b"], require_all=True)
        assert len(results) == 2

    def test_metadata(self) -> None:
        self.registry.register(self.provider1)
        manifest = self.registry.metadata("provider.a")
        assert manifest is not None
        assert manifest.id == "provider.a"

    def test_metadata_nonexistent(self) -> None:
        assert self.registry.metadata("nonexistent") is None

    def test_capabilities(self) -> None:
        self.registry.register(self.provider1)
        caps = self.registry.capabilities("provider.a")
        assert len(caps) == 2
        assert caps[0].id == "cap.a"

    def test_capabilities_nonexistent(self) -> None:
        assert self.registry.capabilities("nonexistent") == []

    def test_all_capabilities(self) -> None:
        self.registry.register(self.provider1)
        self.registry.register(self.provider2)
        all_caps = self.registry.all_capabilities()
        assert len(all_caps) == 2
        assert "provider.a" in all_caps
        assert "provider.b" in all_caps

    def test_count(self) -> None:
        assert self.registry.count == 0
        self.registry.register(self.provider1)
        assert self.registry.count == 1

    def test_health_unknown_provider(self) -> None:
        import asyncio
        health = asyncio.run(self.registry.health("nonexistent"))
        assert health is None

    def test_health_cache(self) -> None:
        self.registry.register(self.provider1)
        assert self.registry.get_cached_health("provider.a") is None

        import asyncio
        asyncio.run(self.registry.health("provider.a"))
        cached = self.registry.get_cached_health("provider.a")
        assert cached is not None
        assert cached.provider_id == "provider.a"

    def test_clear_health_cache(self) -> None:
        self.registry.register(self.provider1)
        import asyncio
        asyncio.run(self.registry.health("provider.a"))
        assert self.registry.get_cached_health("provider.a") is not None
        self.registry.clear_health_cache()
        assert self.registry.get_cached_health("provider.a") is None
