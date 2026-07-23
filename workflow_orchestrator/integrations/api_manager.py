"""API Manager — manages REST API provider connections.

Handles:
- Authentication
- Health checks
- Rate limits
- Connection pools
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


@dataclass
class ApiProviderInfo:
    """Information about an API provider connection.

    Attributes:
        name: Provider name.
        base_url: Base URL for API calls.
        auth_type: Authentication type (api_key, oauth, bearer).
        health_status: Current health status.
        rate_limit: Requests per minute limit.
        latency_ms: Average response latency.
        last_checked: ISO-8601 timestamp.
    """

    name: str = ""
    base_url: str = ""
    auth_type: str = "api_key"
    health_status: str = "unknown"
    rate_limit: int = 0
    latency_ms: float = 0.0
    last_checked: str = ""


class ApiManager:
    """Manages REST API provider connections.

    Handles authentication, health checking, rate limit tracking,
    and connection lifecycle for all API-based providers.

    Usage:
        >>> mgr = ApiManager()
        >>> mgr.register("claude", "https://api.anthropic.com", "api_key")
        >>> health = mgr.check_health("claude")
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the API Manager.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus
        self._providers: dict[str, ApiProviderInfo] = {}

    def register(
        self, name: str, base_url: str, auth_type: str = "api_key",
    ) -> ApiProviderInfo:
        """Register an API provider.

        Args:
            name: Provider name.
            base_url: Base URL for API calls.
            auth_type: Authentication type.

        Returns:
            The created ApiProviderInfo.
        """
        info = ApiProviderInfo(
            name=name,
            base_url=base_url,
            auth_type=auth_type,
        )
        self._providers[name] = info
        return info

    def unregister(self, name: str) -> bool:
        """Unregister an API provider.

        Args:
            name: Provider name.

        Returns:
            True if unregistered.
        """
        return self._providers.pop(name, None) is not None

    def check_health(self, name: str, timeout: int = 10) -> dict[str, Any]:
        """Check the health of an API provider.

        Args:
            name: Provider name.
            timeout: Request timeout in seconds.

        Returns:
            Dict with health check results.
        """
        info = self._providers.get(name)
        if info is None:
            return {"healthy": False, "error": f"Provider '{name}' not found"}

        import subprocess
        import json

        start = time.time()
        try:
            # Simple curl-based health check
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", str(timeout), info.base_url],
                capture_output=True, text=True, timeout=timeout + 2,
            )
            latency = (time.time() - start) * 1000
            status_code = result.stdout.strip()

            healthy = status_code.startswith("2") or status_code.startswith("3")
            info.health_status = "healthy" if healthy else "degraded"
            info.latency_ms = latency
            info.last_checked = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            return {
                "healthy": healthy,
                "status_code": int(status_code) if status_code else 0,
                "latency_ms": round(latency, 2),
            }

        except Exception as exc:
            info.health_status = "unhealthy"
            info.last_checked = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            return {"healthy": False, "error": str(exc)}

    def check_all_health(self) -> dict[str, dict[str, Any]]:
        """Check health of all registered providers.

        Returns:
            Dict mapping provider name to health results.
        """
        return {name: self.check_health(name) for name in self._providers}

    def get_provider(self, name: str) -> ApiProviderInfo | None:
        """Get provider info by name.

        Args:
            name: Provider name.

        Returns:
            ApiProviderInfo or None.
        """
        return self._providers.get(name)

    def list_providers(self) -> list[ApiProviderInfo]:
        """List all registered API providers.

        Returns:
            List of ApiProviderInfo objects.
        """
        return list(self._providers.values())
