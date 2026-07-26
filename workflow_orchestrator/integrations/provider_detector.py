"""Provider Detector — automatically detects installed providers on the system.

Scans the system for:
- Claude Desktop (macOS: ~/Library/Application Support/Claude)
- Claude Code (CLI: claude command)
- ChatGPT Desktop (macOS: /Applications/ChatGPT.app)
- Gemini CLI (CLI: gemini command)
- Cursor (application)
- Codex CLI (CLI: codex command)
- GitHub Copilot (VS Code extension)
- Continue (VS Code extension)
- OpenCode (CLI)
- FreeBuff (CLI)
- Any provider with an executable in PATH
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


@dataclass
class DetectedProvider:
    """A provider detected on the system.

    Attributes:
        provider_id: Unique provider identifier.
        name: Human-readable name.
        version: Detected version string.
        transport: Detected transport type (cli, rest_api, desktop, browser).
        path: Path to the provider executable or application.
        detected_from: How the provider was detected.
        available: Whether the provider is usable.
    """

    provider_id: str = ""
    name: str = ""
    version: str = ""
    transport: str = ""
    path: str = ""
    detected_from: str = ""
    available: bool = False
    unavailable_reason: str = ""


class ProviderDetector:
    """Scans the system for installed AI provider applications and CLIs.

    Uses OS-specific detection logic for each known provider.
    All detection is file-system based — no API calls are made.

    Usage:
        >>> detector = ProviderDetector()
        >>> providers = detector.detect_all()
        >>> for p in providers:
        ...     print(f"{p.name}: {p.transport}")
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Provider Detector.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect_all(self) -> list[DetectedProvider]:
        """Detect all installed providers.

        Returns:
            List of DetectedProvider objects.
        """
        detected: list[DetectedProvider] = []
        detectors = [
            self._detect_claude_desktop,
            self._detect_claude_code,
            self._detect_chatgpt_desktop,
            self._detect_gemini_cli,
            self._detect_cursor,
            self._detect_codex_cli,
            self._detect_copilot,
            self._detect_continue,
            self._detect_opencode,
            self._detect_freebuff,
            self._detect_ollama,
            self._detect_openrouter,
        ]

        for detector in detectors:
            try:
                provider = detector()
                detected.append(provider)
                if provider.available:
                    self._publish_event("integration.provider_detected", {
                        "provider_id": provider.provider_id,
                        "transport": provider.transport,
                        "version": provider.version,
                    })
            except Exception:
                continue

        logger.info("Detected %d total provider statuses", len(detected))
        return detected

    def _detect_claude_desktop(self) -> DetectedProvider:
        """Detect Claude Desktop application."""
        # macOS
        claude_path = Path.home() / "Library" / "Application Support" / "Claude"
        if claude_path.exists():
            return DetectedProvider(
                provider_id="anthropic.claude",
                name="Claude Desktop",
                version="detected",
                transport="desktop",
                path=str(claude_path),
                detected_from="macOS Application Support",
                available=True,
                unavailable_reason="",
            )
        # Windows
        win_claude = Path(os.environ.get("LOCALAPPDATA", "")) / "Claude"
        if win_claude.exists():
            return DetectedProvider(
                provider_id="anthropic.claude",
                name="Claude Desktop",
                version="detected",
                transport="desktop",
                path=str(win_claude),
                detected_from="Windows AppData",
                available=True,
                unavailable_reason="",
            )
        return DetectedProvider(
            provider_id="anthropic.claude",
            name="Claude Desktop",
            available=False,
            unavailable_reason="Claude Desktop App directory not found in AppData/Application Support",
        )

    def _detect_claude_code(self) -> DetectedProvider:
        """Detect Claude Code CLI."""
        claude_path = shutil.which("claude")
        if claude_path:
            version = ""
            try:
                result = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=5)
                version = result.stdout.strip() or result.stderr.strip()
            except Exception:
                pass
            return DetectedProvider(
                provider_id="anthropic.claude",
                name="Claude Code",
                version=version or "detected",
                transport="cli",
                path=claude_path,
                detected_from="PATH",
                available=True,
                unavailable_reason="",
            )
        return DetectedProvider(
            provider_id="anthropic.claude",
            name="Claude Code",
            available=False,
            unavailable_reason="'claude' executable not found on PATH",
        )

    def _detect_chatgpt_desktop(self) -> DetectedProvider:
        """Detect ChatGPT Desktop application."""
        # macOS
        chatgpt_path = Path("/Applications/ChatGPT.app")
        if chatgpt_path.exists():
            return DetectedProvider(
                provider_id="openai.chatgpt",
                name="ChatGPT Desktop",
                version="detected",
                transport="desktop",
                path=str(chatgpt_path),
                detected_from="/Applications",
                available=True,
                unavailable_reason="",
            )
        return DetectedProvider(
            provider_id="openai.chatgpt",
            name="ChatGPT Desktop",
            available=False,
            unavailable_reason="ChatGPT Desktop App not found in /Applications",
        )

    def _detect_gemini_cli(self) -> DetectedProvider:
        """Detect Gemini CLI."""
        gemini_path = shutil.which("gemini")
        if gemini_path:
            return DetectedProvider(
                provider_id="google.gemini",
                name="Gemini CLI",
                version="detected",
                transport="cli",
                path=gemini_path,
                detected_from="PATH",
                available=True,
                unavailable_reason="",
            )
        return DetectedProvider(
            provider_id="google.gemini",
            name="Gemini CLI",
            available=False,
            unavailable_reason="'gemini' executable not found on PATH",
        )

    def _detect_cursor(self) -> DetectedProvider:
        """Detect Cursor editor."""
        cursor_path = shutil.which("cursor")
        if cursor_path:
            return DetectedProvider(
                provider_id="cursor",
                name="Cursor",
                version="detected",
                transport="desktop",
                path=cursor_path,
                detected_from="PATH",
                available=True,
                unavailable_reason="",
            )
        # macOS
        mac_cursor = Path("/Applications/Cursor.app")
        if mac_cursor.exists():
            return DetectedProvider(
                provider_id="cursor",
                name="Cursor",
                version="detected",
                transport="desktop",
                path=str(mac_cursor),
                detected_from="/Applications",
                available=True,
                unavailable_reason="",
            )
        return DetectedProvider(
            provider_id="cursor",
            name="Cursor",
            available=False,
            unavailable_reason="'cursor' executable or /Applications/Cursor.app not found",
        )

    def _detect_codex_cli(self) -> DetectedProvider:
        """Detect Codex CLI."""
        codex_path = shutil.which("codex")
        if codex_path:
            return DetectedProvider(
                provider_id="codex",
                name="Codex CLI",
                version="detected",
                transport="cli",
                path=codex_path,
                detected_from="PATH",
                available=True,
                unavailable_reason="",
            )
        return DetectedProvider(
            provider_id="codex",
            name="Codex CLI",
            available=False,
            unavailable_reason="'codex' executable not found on PATH",
        )

    def _detect_copilot(self) -> DetectedProvider:
        """Detect GitHub Copilot."""
        # Check VS Code extension
        vscode_extensions = Path.home() / ".vscode" / "extensions"
        if vscode_extensions.exists():
            for ext in vscode_extensions.glob("github.copilot-*"):
                return DetectedProvider(
                    provider_id="github.copilot",
                    name="GitHub Copilot",
                    version="detected",
                    transport="desktop",
                    path=str(ext),
                    detected_from="VS Code extensions",
                    available=True,
                    unavailable_reason="",
                )
        return DetectedProvider(
            provider_id="github.copilot",
            name="GitHub Copilot",
            available=False,
            unavailable_reason="~/.vscode/extensions has no github.copilot-* entry",
        )

    def _detect_continue(self) -> DetectedProvider:
        """Detect Continue.dev extension."""
        # Check VS Code extension
        vscode_extensions = Path.home() / ".vscode" / "extensions"
        if vscode_extensions.exists():
            for ext in vscode_extensions.glob("continue.continue-*"):
                return DetectedProvider(
                    provider_id="continue",
                    name="Continue",
                    version="detected",
                    transport="desktop",
                    path=str(ext),
                    detected_from="VS Code extensions",
                    available=True,
                    unavailable_reason="",
                )
        return DetectedProvider(
            provider_id="continue",
            name="Continue",
            available=False,
            unavailable_reason="~/.vscode/extensions has no continue.continue-* entry",
        )

    def _detect_opencode(self) -> DetectedProvider:
        """Detect OpenCode CLI."""
        opencode_path = shutil.which("opencode")
        if opencode_path:
            return DetectedProvider(
                provider_id="opencode",
                name="OpenCode",
                version="detected",
                transport="cli",
                path=opencode_path,
                detected_from="PATH",
                available=True,
                unavailable_reason="",
            )
        return DetectedProvider(
            provider_id="opencode",
            name="OpenCode",
            available=False,
            unavailable_reason="'opencode' executable not found on PATH",
        )

    def _detect_freebuff(self) -> DetectedProvider:
        """Detect FreeBuff CLI."""
        freebuff_path = shutil.which("freebuff")
        if freebuff_path:
            return DetectedProvider(
                provider_id="freebuff",
                name="FreeBuff",
                version="detected",
                transport="cli",
                path=freebuff_path,
                detected_from="PATH",
                available=True,
                unavailable_reason="",
            )
        return DetectedProvider(
            provider_id="freebuff",
            name="FreeBuff",
            available=False,
            unavailable_reason="'freebuff' executable not found on PATH",
        )

    def _detect_ollama(self) -> DetectedProvider:
        """Detect Ollama local engine."""
        ollama_path = shutil.which("ollama")
        if ollama_path:
            return DetectedProvider(
                provider_id="ollama",
                name="Ollama",
                version="detected",
                transport="local",
                path=ollama_path,
                detected_from="PATH",
                available=True,
                unavailable_reason="",
            )
        # Fall back to HTTP probe of http://127.0.0.1:11434/api/tags
        try:
            import urllib.request
            req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return DetectedProvider(
                        provider_id="ollama",
                        name="Ollama",
                        version="detected",
                        transport="local",
                        path="http://127.0.0.1:11434",
                        detected_from="http://127.0.0.1:11434",
                        available=True,
                        unavailable_reason="",
                    )
        except Exception:
            pass

        return DetectedProvider(
            provider_id="ollama",
            name="Ollama",
            transport="local",
            available=False,
            detected_from="system_scan",
            unavailable_reason="'ollama' binary not found on PATH and http://127.0.0.1:11434 not responding",
        )

    def _detect_openrouter(self) -> DetectedProvider:
        """Detect OpenRouter API service via environment key."""
        has_key = bool(os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_KEY"))
        if has_key:
            return DetectedProvider(
                provider_id="openrouter",
                name="OpenRouter",
                version="cloud",
                transport="rest_api",
                detected_from="OPENROUTER_API_KEY env var",
                available=True,
                unavailable_reason="",
            )
        return DetectedProvider(
            provider_id="openrouter",
            name="OpenRouter",
            version="cloud",
            transport="rest_api",
            detected_from="cloud_api",
            available=False,
            unavailable_reason="OpenRouter API key not configured in environment",
        )

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(type=event_type, data=data, source="provider_detector"))
        except Exception:
            pass
