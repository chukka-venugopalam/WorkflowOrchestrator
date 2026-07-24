"""Capability registry for indexing, discovery, and resolution.

The Capability Registry manages what capabilities (abilities) are
available in the system.  It supports registration, discovery,
metadata management, validation, and search.

Capability IDs are namespaced:
- Built-in: ``codegen.*``, ``reasoning.*``, ``verify.*``, ``deploy.*``, ``tool.*``
- Community: ``community.author.capability-name``
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CandidateHealth(Enum):
    """Health status of a capability candidate."""

    UNKNOWN = "unknown"
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class CostTier(Enum):
    """Cost tier for a capability candidate."""

    FREE = "free"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PREMIUM = "premium"


class QualityLevel(Enum):
    """Quality level for a capability candidate."""

    EXPERIMENTAL = "experimental"
    BETA = "beta"
    STABLE = "stable"
    GOLD = "gold"
    PLATINUM = "platinum"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class CapabilityManifest:
    """Metadata about a capability implementation.

    Attributes:
        id: Unique namespaced capability ID (e.g., ``codegen.nextjs``).
        name: Human-readable name.
        description: Description of what this capability does.
        provider_id: ID of the provider that offers this capability.
        version: Version string.
        cost_tier: Cost tier.
        quality: Quality level.
        health: Current health status.
        tags: Optional tags for filtering.
        metadata: Additional implementation-specific metadata.
    """

    id: str
    name: str = ""
    description: str = ""
    provider_id: str = ""
    version: str = "1.0.0"
    cost_tier: CostTier = CostTier.MEDIUM
    quality: QualityLevel = QualityLevel.STABLE
    health: CandidateHealth = CandidateHealth.UNKNOWN
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CapabilityManifest:
        """Create from a dictionary."""
        cost_tier = data.get("cost_tier", "medium")
        quality = data.get("quality", "stable")
        health = data.get("health", "unknown")

        try:
            cost_tier_enum = CostTier(cost_tier)
        except ValueError:
            cost_tier_enum = CostTier.MEDIUM

        try:
            quality_enum = QualityLevel(quality)
        except ValueError:
            quality_enum = QualityLevel.STABLE

        try:
            health_enum = CandidateHealth(health)
        except ValueError:
            health_enum = CandidateHealth.UNKNOWN

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            provider_id=data.get("provider_id", ""),
            version=data.get("version", "1.0.0"),
            cost_tier=cost_tier_enum,
            quality=quality_enum,
            health=health_enum,
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "provider_id": self.provider_id,
            "version": self.version,
            "cost_tier": self.cost_tier.value,
            "quality": self.quality.value,
            "health": self.health.value,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class CapabilityRequirement:
    """A requirement that must be resolved to a capability.

    Attributes:
        capability_id: The capability ID pattern to match.
        min_quality: Minimum acceptable quality level.
        max_cost_tier: Maximum acceptable cost tier.
        exclude_providers: Provider IDs to exclude.
        tags_required: Required tags that must be present.
    """

    capability_id: str
    min_quality: QualityLevel = QualityLevel.BETA
    max_cost_tier: CostTier = CostTier.HIGH
    exclude_providers: list[str] = field(default_factory=list)
    tags_required: list[str] = field(default_factory=list)


@dataclass
class RankedCandidates:
    """Result of a capability resolution.

    Attributes:
        requirement: The original requirement.
        candidates: Ranked list of matching manifests.
        trace: Resolution trace for debugging.
    """

    requirement: CapabilityRequirement
    candidates: list[CapabilityManifest] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)


@dataclass
class ProviderMetadata:
    """Metadata about a capability provider.

    Attributes:
        provider_id: Unique provider identifier.
        name: Human-readable provider name.
        description: Description of the provider.
        version: Provider version.
        capabilities: List of capability IDs this provider offers.
        health: Overall provider health.
    """

    provider_id: str
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    capabilities: list[str] = field(default_factory=list)
    health: CandidateHealth = CandidateHealth.UNKNOWN


# ---------------------------------------------------------------------------
# Capability Taxonomy
# ---------------------------------------------------------------------------


class CapabilityTaxonomy:
    """Built-in capability taxonomy.

    Provides the canonical list of known capability IDs and their
    hierarchical relationships.
    """

    # Built-in capability namespace prefixes
    NAMESPACES = {
        "codegen": "Code generation (e.g., codegen.nextjs, codegen.python-api)",
        "reasoning": "Reasoning and analysis (e.g., reasoning.code-review, reasoning.architecture)",
        "verify": "Verification (e.g., verify.build, verify.test, verify.lint)",
        "deploy": "Deployment (e.g., deploy.vercel, deploy.render)",
        "tool": "Tool operations (e.g., tool.git, tool.terminal, tool.browser)",
    }

    @staticmethod
    def validate_id(capability_id: str) -> bool:
        """Validate a capability ID format.

        A valid ID is namespaced with at least two parts:
        ``namespace.name`` or ``namespace.subnamespace.name``.

        Args:
            capability_id: The ID to validate.

        Returns:
            True if the ID format is valid.
        """
        parts = capability_id.split(".")
        if len(parts) < 2:
            return False
        if not all(part.isidentifier() or part.replace("-", "").isalnum() for part in parts):
            return False
        return True

    @staticmethod
    def is_builtin(capability_id: str) -> bool:
        """Check if a capability ID belongs to a built-in namespace.

        Args:
            capability_id: The ID to check.

        Returns:
            True if the ID starts with a built-in namespace.
        """
        namespace = capability_id.split(".")[0]
        return namespace in CapabilityTaxonomy.NAMESPACES

    @staticmethod
    def is_community(capability_id: str) -> bool:
        """Check if a capability ID is a community extension.

        Args:
            capability_id: The ID to check.

        Returns:
            True if the ID starts with ``community``.
        """
        return capability_id.startswith("community.")


# ---------------------------------------------------------------------------
# Capability Registry
# ---------------------------------------------------------------------------


class CapabilityRegistry:
    """Registry for capability manifests and providers.

    Supports:
    - Register and deregister capability manifests
    - Register provider metadata
    - Resolve capability requirements to ranked candidates
    - Search and filter capabilities
    - Health tracking

    Usage:
        >>> registry = CapabilityRegistry()
        >>> registry.register(CapabilityManifest(id="codegen.nextjs", provider_id="claude"))
        >>> result = registry.resolve(CapabilityRequirement(capability_id="codegen.nextjs"))
        >>> print(result.candidates[0].provider_id)
        'claude'
    """

    def __init__(self) -> None:
        self._capabilities: dict[str, list[CapabilityManifest]] = {}
        self._providers: dict[str, ProviderMetadata] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, manifest: CapabilityManifest) -> None:
        """Register a capability manifest.

        Args:
            manifest: The capability manifest to register.
        """
        if not CapabilityTaxonomy.validate_id(manifest.id):
            raise ValueError(
                f"Invalid capability ID '{manifest.id}'. "
                "Must be namespaced (e.g., 'codegen.nextjs')."
            )

        if manifest.id not in self._capabilities:
            self._capabilities[manifest.id] = []
        self._capabilities[manifest.id].append(manifest)

        # Update provider's capability list
        if manifest.provider_id:
            provider = self._providers.get(manifest.provider_id)
            if provider:
                if manifest.id not in provider.capabilities:
                    provider.capabilities.append(manifest.id)

        logger.debug("Registered capability '%s' (provider: %s)", manifest.id, manifest.provider_id)

    def deregister(self, capability_id: str, provider_id: str | None = None) -> int:
        """Deregister capability manifests.

        Args:
            capability_id: The capability ID to deregister.
            provider_id: If provided, only deregister manifests from this provider.

        Returns:
            Number of manifests deregistered.
        """
        if provider_id:
            manifests = self._capabilities.get(capability_id, [])
            filtered = [m for m in manifests if m.provider_id != provider_id]
            removed = len(manifests) - len(filtered)
            if filtered:
                self._capabilities[capability_id] = filtered
            else:
                self._capabilities.pop(capability_id, None)
            return removed
        else:
            manifests = self._capabilities.pop(capability_id, [])
            return len(manifests)

    def register_provider(self, metadata: ProviderMetadata) -> None:
        """Register provider metadata.

        Args:
            metadata: The provider metadata to register.
        """
        self._providers[metadata.provider_id] = metadata
        logger.debug("Registered provider '%s'", metadata.provider_id)

    def deregister_provider(self, provider_id: str) -> None:
        """Deregister a provider and all its capabilities.

        Args:
            provider_id: The provider ID to deregister.
        """
        self._providers.pop(provider_id, None)
        # Remove all capabilities from this provider
        for cap_id in list(self._capabilities.keys()):
            self.deregister(cap_id, provider_id=provider_id)

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def resolve(self, requirement: CapabilityRequirement) -> RankedCandidates:
        """Resolve a capability requirement to ranked candidates.

        Resolution algorithm:
        1. Filter by capability ID match + hard constraints
        2. Exclude ``Unavailable`` candidates
        3. Sort by: user pin, quality descending, cost tier ascending, latency
        4. Return ranked list

        Args:
            requirement: The capability requirement.

        Returns:
            RankedCandidates with sorted candidates and resolution trace.
        """
        trace: list[str] = []
        candidates: list[CapabilityManifest] = []

        # Step 1: Find all manifests matching the capability ID
        matching = self._capabilities.get(requirement.capability_id, [])
        trace.append(f"Found {len(matching)} raw candidates for '{requirement.capability_id}'")

        # Step 2: Filter by constraints
        for manifest in matching:
            # Exclude unavailable
            if manifest.health == CandidateHealth.UNAVAILABLE:
                trace.append(f"  Excluded '{manifest.provider_id}' (unavailable)")
                continue

            # Exclude by provider
            if manifest.provider_id in requirement.exclude_providers:
                trace.append(f"  Excluded '{manifest.provider_id}' (excluded by requirement)")
                continue

            # Quality filter
            quality_order = [q.value for q in QualityLevel]
            if quality_order.index(manifest.quality.value) < quality_order.index(requirement.min_quality.value):
                trace.append(f"  Excluded '{manifest.provider_id}' (quality: {manifest.quality.value}, need >= {requirement.min_quality.value})")
                continue

            # Cost filter
            cost_order = [c.value for c in CostTier]
            if cost_order.index(manifest.cost_tier.value) > cost_order.index(requirement.max_cost_tier.value):
                trace.append(f"  Excluded '{manifest.provider_id}' (cost: {manifest.cost_tier.value}, need <= {requirement.max_cost_tier.value})")
                continue

            candidates.append(manifest)
            trace.append(f"  Included '{manifest.provider_id}' (quality={manifest.quality.value}, cost={manifest.cost_tier.value})")

        # Step 3: Sort by quality descending, then cost tier ascending
        quality_rank = {q.value: i for i, q in enumerate(QualityLevel)}
        cost_rank = {c.value: i for i, c in enumerate(CostTier)}

        def _sort_key(m: CapabilityManifest) -> tuple:
            return (
                -quality_rank.get(m.quality.value, 0),
                cost_rank.get(m.cost_tier.value, 0),
            )

        candidates.sort(key=_sort_key)
        trace.append(f"Sorted {len(candidates)} candidates")

        return RankedCandidates(
            requirement=requirement,
            candidates=candidates,
            trace=trace,
        )

    # ------------------------------------------------------------------
    # Discovery / Search
    # ------------------------------------------------------------------

    def list_capabilities(self) -> list[CapabilityManifest]:
        """List all registered capability manifests.

        Returns:
            Flat list of all capability manifests.
        """
        result: list[CapabilityManifest] = []
        for manifests in self._capabilities.values():
            result.extend(manifests)
        return result

    def list_capability_ids(self) -> list[str]:
        """List all unique capability IDs.

        Returns:
            Sorted list of capability IDs.
        """
        return sorted(self._capabilities.keys())

    def list_providers(self) -> list[ProviderMetadata]:
        """List all registered providers.

        Returns:
            List of ProviderMetadata objects.
        """
        return list(self._providers.values())

    def find_by_id(self, capability_id: str) -> list[CapabilityManifest]:
        """Find all manifests for a specific capability ID.

        Args:
            capability_id: The capability ID to look up.

        Returns:
            List of matching manifests.
        """
        return list(self._capabilities.get(capability_id, []))

    def find_by_provider(self, provider_id: str) -> list[CapabilityManifest]:
        """Find all capabilities offered by a provider.

        Args:
            provider_id: The provider ID.

        Returns:
            List of capability manifests from this provider.
        """
        return [m for manifests in self._capabilities.values() for m in manifests if m.provider_id == provider_id]

    def search(self, query: str) -> list[CapabilityManifest]:
        """Search capabilities by ID, name, or description.

        Args:
            query: Search string.

        Returns:
            List of matching capability manifests.
        """
        query_lower = query.lower()
        results: list[CapabilityManifest] = []
        for manifests in self._capabilities.values():
            for manifest in manifests:
                if (query_lower in manifest.id.lower()
                        or query_lower in manifest.name.lower()
                        or query_lower in manifest.description.lower()
                        or any(query_lower in tag.lower() for tag in manifest.tags)):
                    results.append(manifest)
        return results

    # ------------------------------------------------------------------
    # Health management
    # ------------------------------------------------------------------

    def update_health(self, capability_id: str, provider_id: str, health: CandidateHealth) -> None:
        """Update the health status of a specific capability.

        Args:
            capability_id: The capability ID.
            provider_id: The provider ID.
            health: New health status.
        """
        manifests = self._capabilities.get(capability_id, [])
        for manifest in manifests:
            if manifest.provider_id == provider_id:
                manifest.health = health
                logger.debug("Updated health of '%s/%s' to %s", provider_id, capability_id, health.value)
                return

        logger.warning(
            "Capability '%s' from provider '%s' not found for health update",
            capability_id,
            provider_id,
        )

    def update_provider_health(self, provider_id: str, health: CandidateHealth) -> None:
        """Update health for all capabilities of a provider.

        Args:
            provider_id: The provider ID.
            health: New health status.
        """
        provider = self._providers.get(provider_id)
        if provider:
            provider.health = health

        for manifests in self._capabilities.values():
            for manifest in manifests:
                if manifest.provider_id == provider_id:
                    manifest.health = health

        logger.debug("Updated all capabilities for provider '%s' to %s", provider_id, health.value)

    @property
    def capability_count(self) -> int:
        """Total number of registered capability manifests."""
        return sum(len(manifests) for manifests in self._capabilities.values())

    @property
    def provider_count(self) -> int:
        """Number of registered providers."""
        return len(self._providers)
