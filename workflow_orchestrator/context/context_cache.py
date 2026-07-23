"""Context cache — cache context assemblies for reuse across steps.

Deterministic caching based on content hashing.
Reuses context when inputs haven't changed to avoid reassembly.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from workflow_orchestrator.context.context_models import (
    ContextAssembly,
    ContextCacheEntry,
)

logger = logging.getLogger(__name__)


class ContextCache:
    """Cache for context assemblies to avoid redundant assembly.

    Uses content-based hashing for deterministic cache keys.
    Supports TTL-based expiration.

    Usage:
        >>> cache = ContextCache(max_size=100, ttl_seconds=300)
        >>> key = cache.make_key({"contract": "...", "state": {...}})
        >>> cached = cache.get(key)
        >>> if cached is None:
        ...     assembly = assemble_context(...)
        ...     cache.put(key, assembly)
    """

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300) -> None:
        """Initialize the context cache.

        Args:
            max_size: Maximum number of cache entries.
            ttl_seconds: Time-to-live in seconds for cache entries.
        """
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._cache: dict[str, ContextCacheEntry] = {}

    def make_key(self, inputs: dict[str, Any]) -> str:
        """Create a deterministic cache key from inputs.

        Args:
            inputs: Dict of context inputs.

        Returns:
            A hex digest cache key.
        """
        sorted_items = sorted(inputs.items(), key=lambda x: x[0])
        serialized = str(sorted_items)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    def get(self, key: str) -> ContextAssembly | None:
        """Get a cached context assembly.

        Args:
            key: The cache key.

        Returns:
            The cached ContextAssembly, or None if miss or expired.
        """
        entry = self._cache.get(key)
        if entry is None:
            return None

        if self._is_expired(entry):
            self._cache.pop(key, None)
            return None

        entry.hit_count += 1
        logger.debug("Cache hit: '%s' (hits: %d)", key[:8], entry.hit_count)
        return entry.assembly

    def put(self, key: str, assembly: ContextAssembly) -> None:
        """Store a context assembly in the cache.

        Args:
            key: The cache key.
            assembly: The context assembly to cache.
        """
        if len(self._cache) >= self._max_size:
            self._evict_oldest()

        now = datetime.now(timezone.utc).isoformat()
        expires = datetime.fromtimestamp(time.time() + self._ttl_seconds, tz=timezone.utc).isoformat()

        entry = ContextCacheEntry(
            cache_key=key,
            assembly=assembly,
            hit_count=0,
            created_at=now,
            expires_at=expires,
        )
        self._cache[key] = entry
        logger.debug("Cache put: '%s' (%d tokens)", key[:8], assembly.total_tokens)

    def get_or_compute(
        self,
        key: str,
        compute_fn: Any,
    ) -> ContextAssembly:
        """Get from cache or compute and store.

        Args:
            key: The cache key.
            compute_fn: Callable that returns a ContextAssembly.

        Returns:
            The cached or freshly computed ContextAssembly.
        """
        cached = self.get(key)
        if cached is not None:
            return cached

        assembly = compute_fn()
        self.put(key, assembly)
        return assembly

    def invalidate(self, key: str) -> bool:
        """Invalidate a cache entry.

        Args:
            key: The cache key to invalidate.

        Returns:
            True if invalidated, False if not found.
        """
        return self._cache.pop(key, None) is not None

    def invalidate_all(self) -> None:
        """Invalidate all cache entries."""
        self._cache.clear()
        logger.debug("Cache invalidated all entries")

    def _is_expired(self, entry: ContextCacheEntry) -> bool:
        """Check if a cache entry is expired.

        Args:
            entry: The cache entry to check.

        Returns:
            True if expired.
        """
        try:
            expires = datetime.fromisoformat(entry.expires_at)
            return datetime.now(timezone.utc) > expires.replace(tzinfo=timezone.utc) if expires.tzinfo else datetime.now(timezone.utc) > expires
        except (ValueError, AttributeError):
            return False

    def _evict_oldest(self) -> None:
        """Evict the oldest cache entry."""
        if not self._cache:
            return
        oldest_key = min(self._cache, key=lambda k: self._cache[k].created_at)
        self._cache.pop(oldest_key, None)
        logger.debug("Evicted oldest cache entry: '%s'", oldest_key[:8])

    @property
    def size(self) -> int:
        """Current number of cache entries."""
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        """Cache hit rate across all entries."""
        total_hits = sum(e.hit_count for e in self._cache.values())
        total = total_hits + self.size
        return total_hits / max(total, 1)
