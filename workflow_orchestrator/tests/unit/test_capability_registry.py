"""Unit tests for the CapabilityRegistry."""

from __future__ import annotations

import pytest
from workflow_orchestrator.core.capability_registry import (
    CapabilityRegistry,
    CapabilityManifest,
    CapabilityRequirement,
    CapabilityTaxonomy,
    CandidateHealth,
    CostTier,
    QualityLevel,
    ProviderMetadata,
)


class TestCapabilityTaxonomy:
    """Test suite for CapabilityTaxonomy."""

    def test_valid_namespaced_id(self) -> None:
        assert CapabilityTaxonomy.validate_id("codegen.nextjs")
        assert CapabilityTaxonomy.validate_id("deploy.vercel")
        assert CapabilityTaxonomy.validate_id("community.author.my-capability")
        assert CapabilityTaxonomy.validate_id("verify.build.lint")

    def test_invalid_id(self) -> None:
        assert not CapabilityTaxonomy.validate_id("simple")
        assert not CapabilityTaxonomy.validate_id("")
        assert not CapabilityTaxonomy.validate_id("has spaces.nope")

    def test_is_builtin(self) -> None:
        assert CapabilityTaxonomy.is_builtin("codegen.python")
        assert CapabilityTaxonomy.is_builtin("deploy.vercel")
        assert not CapabilityTaxonomy.is_builtin("community.custom.test")

    def test_is_community(self) -> None:
        assert CapabilityTaxonomy.is_community("community.author.test")
        assert not CapabilityTaxonomy.is_community("codegen.test")


class TestCapabilityRegistry:
    """Test suite for CapabilityRegistry."""

    def setup_method(self) -> None:
        self.registry = CapabilityRegistry()

    def test_register_and_list(self) -> None:
        """Test registering a capability and listing it."""
        manifest = CapabilityManifest(
            id="codegen.nextjs",
            name="Next.js Code Generation",
            provider_id="claude",
            quality=QualityLevel.STABLE,
            cost_tier=CostTier.MEDIUM,
        )
        self.registry.register(manifest)

        capabilities = self.registry.list_capabilities()
        assert len(capabilities) == 1
        assert capabilities[0].id == "codegen.nextjs"

    def test_register_invalid_id_raises(self) -> None:
        """Test that registering an invalid ID raises ValueError."""
        manifest = CapabilityManifest(id="invalid")
        with pytest.raises(ValueError, match="Invalid capability ID"):
            self.registry.register(manifest)

    def test_deregister_by_id(self) -> None:
        """Test deregistering all manifests for a capability ID."""
        self.registry.register(CapabilityManifest(id="codegen.test", provider_id="p1"))
        self.registry.register(CapabilityManifest(id="codegen.test", provider_id="p2"))

        assert len(self.registry.list_capabilities()) == 2
        removed = self.registry.deregister("codegen.test")
        assert removed == 2
        assert len(self.registry.list_capabilities()) == 0

    def test_deregister_by_provider(self) -> None:
        """Test deregistering manifests from a specific provider."""
        self.registry.register(CapabilityManifest(id="codegen.a", provider_id="p1"))
        self.registry.register(CapabilityManifest(id="codegen.b", provider_id="p2"))

        removed = self.registry.deregister("codegen.a", provider_id="p1")
        assert removed == 1
        assert len(self.registry.list_capabilities()) == 1

    def test_resolve_empty(self) -> None:
        """Test resolving with no candidates."""
        result = self.registry.resolve(
            CapabilityRequirement(capability_id="codegen.nonexistent")
        )
        assert len(result.candidates) == 0
        assert len(result.trace) > 0

    def test_resolve_basic(self) -> None:
        """Test basic capability resolution."""
        self.registry.register(CapabilityManifest(
            id="codegen.nextjs",
            provider_id="claude",
            quality=QualityLevel.STABLE,
            cost_tier=CostTier.MEDIUM,
        ))

        result = self.registry.resolve(
            CapabilityRequirement(capability_id="codegen.nextjs")
        )
        assert len(result.candidates) == 1
        assert result.candidates[0].provider_id == "claude"

    def test_resolve_excludes_unavailable(self) -> None:
        """Test that unavailable candidates are excluded."""
        self.registry.register(CapabilityManifest(
            id="codegen.test",
            provider_id="p1",
            health=CandidateHealth.UNAVAILABLE,
        ))
        self.registry.register(CapabilityManifest(
            id="codegen.test",
            provider_id="p2",
            health=CandidateHealth.AVAILABLE,
        ))

        result = self.registry.resolve(CapabilityRequirement(capability_id="codegen.test"))
        assert len(result.candidates) == 1
        assert result.candidates[0].provider_id == "p2"

    def test_resolve_excludes_by_provider(self) -> None:
        """Test excluding specific providers."""
        self.registry.register(CapabilityManifest(id="codegen.test", provider_id="p1"))
        self.registry.register(CapabilityManifest(id="codegen.test", provider_id="p2"))

        result = self.registry.resolve(
            CapabilityRequirement(capability_id="codegen.test", exclude_providers=["p1"])
        )
        assert len(result.candidates) == 1
        assert result.candidates[0].provider_id == "p2"

    def test_resolve_quality_filter(self) -> None:
        """Test quality-based filtering."""
        self.registry.register(CapabilityManifest(
            id="codegen.test", provider_id="p1", quality=QualityLevel.EXPERIMENTAL,
        ))
        self.registry.register(CapabilityManifest(
            id="codegen.test", provider_id="p2", quality=QualityLevel.GOLD,
        ))

        result = self.registry.resolve(
            CapabilityRequirement(capability_id="codegen.test", min_quality=QualityLevel.STABLE)
        )
        assert len(result.candidates) == 1
        assert result.candidates[0].provider_id == "p2"

    def test_resolve_quality_sorting(self) -> None:
        """Test that candidates are sorted by quality (descending)."""
        self.registry.register(CapabilityManifest(
            id="codegen.test", provider_id="p1", quality=QualityLevel.BETA,
        ))
        self.registry.register(CapabilityManifest(
            id="codegen.test", provider_id="p2", quality=QualityLevel.PLATINUM,
        ))
        self.registry.register(CapabilityManifest(
            id="codegen.test", provider_id="p3", quality=QualityLevel.STABLE,
        ))

        result = self.registry.resolve(CapabilityRequirement(capability_id="codegen.test"))
        assert len(result.candidates) == 3
        # Should be sorted: platinum, stable, beta
        assert result.candidates[0].quality == QualityLevel.PLATINUM
        assert result.candidates[1].quality == QualityLevel.STABLE
        assert result.candidates[2].quality == QualityLevel.BETA

    def test_find_by_id(self) -> None:
        """Test finding manifests by capability ID."""
        self.registry.register(CapabilityManifest(id="codegen.a", provider_id="p1"))
        self.registry.register(CapabilityManifest(id="codegen.b", provider_id="p2"))

        found = self.registry.find_by_id("codegen.a")
        assert len(found) == 1
        assert found[0].provider_id == "p1"

        assert len(self.registry.find_by_id("nonexistent")) == 0

    def test_find_by_provider(self) -> None:
        """Test finding all capabilities from a provider."""
        self.registry.register(CapabilityManifest(id="codegen.a", provider_id="p1"))
        self.registry.register(CapabilityManifest(id="codegen.b", provider_id="p1"))
        self.registry.register(CapabilityManifest(id="deploy.c", provider_id="p2"))

        found = self.registry.find_by_provider("p1")
        assert len(found) == 2

    def test_search(self) -> None:
        """Test searching capabilities."""
        self.registry.register(CapabilityManifest(
            id="codegen.python-api",
            name="Python API Generator",
            description="Generates REST API code for Python",
            tags=["python", "api"],
        ))

        results = self.registry.search("python")
        assert len(results) == 1

        results = self.registry.search("nonexistent")
        assert len(results) == 0

    def test_update_health(self) -> None:
        """Test updating capability health."""
        self.registry.register(CapabilityManifest(
            id="codegen.test", provider_id="p1", health=CandidateHealth.AVAILABLE,
        ))

        self.registry.update_health("codegen.test", "p1", CandidateHealth.DEGRADED)

        manifests = self.registry.find_by_id("codegen.test")
        assert manifests[0].health == CandidateHealth.DEGRADED

    def test_update_provider_health(self) -> None:
        """Test updating health for all capabilities of a provider."""
        self.registry.register(CapabilityManifest(id="codegen.a", provider_id="p1"))
        self.registry.register(CapabilityManifest(id="codegen.b", provider_id="p1"))

        self.registry.update_provider_health("p1", CandidateHealth.DEGRADED)

        for m in self.registry.find_by_provider("p1"):
            assert m.health == CandidateHealth.DEGRADED

    def test_register_provider(self) -> None:
        """Test registering provider metadata."""
        provider = ProviderMetadata(
            provider_id="claude",
            name="Anthropic Claude",
            capabilities=["codegen.nextjs"],
        )
        self.registry.register_provider(provider)

        providers = self.registry.list_providers()
        assert len(providers) == 1
        assert providers[0].provider_id == "claude"

    def test_deregister_provider(self) -> None:
        """Test deregistering a provider and its capabilities."""
        self.registry.register_provider(ProviderMetadata(provider_id="p1"))
        self.registry.register(CapabilityManifest(id="codegen.a", provider_id="p1"))

        self.registry.deregister_provider("p1")
        assert len(self.registry.list_providers()) == 0
        assert len(self.registry.list_capabilities()) == 0

    def test_capability_count(self) -> None:
        """Test the capability_count property."""
        assert self.registry.capability_count == 0
        self.registry.register(CapabilityManifest(id="codegen.a", provider_id="p1"))
        self.registry.register(CapabilityManifest(id="codegen.b", provider_id="p2"))
        assert self.registry.capability_count == 2

    def test_provider_count(self) -> None:
        """Test the provider_count property."""
        assert self.registry.provider_count == 0
        self.registry.register_provider(ProviderMetadata(provider_id="p1"))
        assert self.registry.provider_count == 1

    def test_list_capability_ids(self) -> None:
        """Test listing unique capability IDs."""
        self.registry.register(CapabilityManifest(id="b.test", provider_id="p1"))
        self.registry.register(CapabilityManifest(id="a.test", provider_id="p2"))
        ids = self.registry.list_capability_ids()
        assert ids == ["a.test", "b.test"]  # Sorted
