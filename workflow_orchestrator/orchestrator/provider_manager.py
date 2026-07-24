"""Provider Manager — facade and management for all AI Providers.

Connects ProviderRegistry, ProviderRuntime, ProviderDetector,
ProviderConfiguration, and CredentialManager.

Supports:
- Claude
- ChatGPT
- Gemini
- OpenAI Codex
- Cursor
- GitHub Copilot
- Claude Code
- FreeBuff
- OpenCode
- Codex CLI
- Future providers
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from workflow_orchestrator.integrations.provider_manager import ProviderManager as IntProviderManager, ProviderInfo as IntProviderInfo
from workflow_orchestrator.integrations.provider_detector import ProviderDetector, DetectedProvider
from workflow_orchestrator.integrations.provider_configuration import ProviderConfiguration
from workflow_orchestrator.integrations.credential_manager import CredentialManager
from workflow_orchestrator.intelligence.provider_registry import ProviderRegistry
from workflow_orchestrator.providers.registry.provider_registry_runtime import ProviderRegistryRuntime
from workflow_orchestrator.runtime.provider_runtime import ProviderRuntime

logger = logging.getLogger(__name__)


@dataclass
class ProviderMetadata:
    """Rich provider metadata and capability state."""

    name: str
    provider_id: str
    enabled: bool = True
    priority: int = 10
    cost: str = "medium"
    quality: str = "high"
    speed: str = "fast"
    preferred_transport: str = "rest_api"
    api_key_configured: bool = False
    cli_path: Optional[str] = None
    browser_login: bool = False
    desktop_login: bool = False
    mcp_enabled: bool = False
    health: str = "healthy"
    version: str = "1.0.0"
    status: str = "available"
    authentication_type: str = "api_key"


class ProviderManager:
    """Unified Orchestration Manager for AI Providers.

    Composes existing integrations and runtime services.
    """

    KNOWN_PROVIDERS = [
        "claude",
        "chatgpt",
        "gemini",
        "openai_codex",
        "cursor",
        "github_copilot",
        "claude_code",
        "freebuff",
        "opencode",
        "codex_cli",
    ]

    def __init__(
        self,
        int_provider_manager: Optional[IntProviderManager] = None,
        provider_detector: Optional[ProviderDetector] = None,
        provider_config: Optional[ProviderConfiguration] = None,
        credential_manager: Optional[CredentialManager] = None,
        provider_runtime: Optional[ProviderRuntime] = None,
    ) -> None:
        self.int_manager = int_provider_manager or IntProviderManager()
        self.detector = provider_detector or ProviderDetector()
        self.config_mgr = provider_config or ProviderConfiguration()
        self.cred_mgr = credential_manager or CredentialManager()
        base_reg = ProviderRegistry()
        reg_rt = ProviderRegistryRuntime(registry=base_reg)
        self.runtime = provider_runtime or ProviderRuntime(provider_registry_runtime=reg_rt)

    def discover_and_load(self) -> List[ProviderMetadata]:
        """Discover installed providers and load their current status."""
        detected = self.detector.detect_all()
        detected_ids = {p.provider_id: p for p in detected}

        results: List[ProviderMetadata] = []

        for pid in self.KNOWN_PROVIDERS:
            det = detected_ids.get(pid)
            has_key = self.cred_mgr.has_api_key(f"{pid.upper()}_API_KEY") or self.cred_mgr.has_api_key(f"{pid.upper()}_KEY")
            
            cfg = self.config_mgr.read(pid) or {}
            
            cli_p = getattr(det, "cli_path", getattr(det, "path", None)) if det else cfg.get("cli_path")
            
            meta = ProviderMetadata(
                name=cfg.get("name", pid.replace("_", " ").title()),
                provider_id=pid,
                enabled=cfg.get("enabled", True),
                priority=cfg.get("priority", 10),
                cost=cfg.get("cost", "medium"),
                quality=cfg.get("quality", "high"),
                speed=cfg.get("speed", "fast"),
                preferred_transport=cfg.get("transport", "rest_api"),
                api_key_configured=has_key,
                cli_path=cli_p,
                browser_login=getattr(det, "browser_login", False) if det else False,
                desktop_login=getattr(det, "desktop_login", False) if det else False,
                mcp_enabled=cfg.get("mcp_enabled", False),
                health="healthy" if (det and getattr(det, "available", False)) or has_key else "unknown",
                version=getattr(det, "version", "1.0.0") if det else cfg.get("version", "1.0.0"),
                status="available" if (det and getattr(det, "available", False)) or has_key else "unconfigured",
                authentication_type="api_key" if has_key else ("cli" if cli_p else "none"),
            )
            results.append(meta)

        return results

    def get_provider(self, provider_id: str) -> Optional[ProviderMetadata]:
        """Get provider metadata by ID."""
        providers = self.discover_and_load()
        for p in providers:
            if p.provider_id.lower() == provider_id.lower() or p.name.lower() == provider_id.lower():
                return p
        return None

    def enable_provider(self, provider_id: str) -> bool:
        """Enable a provider."""
        cfg = self.config_mgr.read(provider_id) or {"name": provider_id.title(), "provider_id": provider_id}
        cfg["enabled"] = True
        return self.config_mgr.write(provider_id, cfg)

    def disable_provider(self, provider_id: str) -> bool:
        """Disable a provider."""
        cfg = self.config_mgr.read(provider_id) or {"name": provider_id.title(), "provider_id": provider_id}
        cfg["enabled"] = False
        return self.config_mgr.write(provider_id, cfg)

    def configure_provider(self, provider_id: str, api_key: Optional[str] = None, **kwargs: Any) -> bool:
        """Set configuration and API key for a provider."""
        if api_key:
            key_name = f"{provider_id.upper()}_API_KEY"
            self.cred_mgr.set_api_key(key_name, api_key)

        cfg = self.config_mgr.read(provider_id) or {"name": provider_id.title(), "provider_id": provider_id}
        for k, v in kwargs.items():
            cfg[k] = v
        return self.config_mgr.write(provider_id, cfg)

    def list_enabled(self) -> List[ProviderMetadata]:
        """Return all enabled providers."""
        return [p for p in self.discover_and_load() if p.enabled]
