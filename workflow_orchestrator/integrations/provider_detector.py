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
        ]

        for detector in detectors:
            try:
                provider = detector()
                if provider.available:
                    detected.append(provider)
                    self._publish_event("integration.provider_detected", {
                        "provider_id": provider.provider_id,
                        "transport": provider.transport,
                        "version": provider.version,
                    })
            except Exception:
                continue

        logger.info("Detected %d installed providers", len(detected))
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
            )
        return DetectedProvider(provider_id="anthropic.claude", name="Claude Desktop")

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
            )
        return DetectedProvider(provider_id="anthropic.claude", name="Claude Code")

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
            )
        return DetectedProvider(provider_id="openai.chatgpt", name="ChatGPT Desktop")

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
            )
        return DetectedProvider(provider_id="google.gemini", name="Gemini CLI")

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
            )
        return DetectedProvider(provider_id="cursor", name="Cursor")

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
            )
        return DetectedProvider(provider_id="codex", name="Codex CLI")

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
                )
        return DetectedProvider(provider_id="github.copilot", name="GitHub Copilot")

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
                )
        return DetectedProvider(provider_id="continue", name="Continue")

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
            )
        return DetectedProvider(provider_id="opencode", name="OpenCode")

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
            )
        return DetectedProvider(provider_id="freebuff", name="FreeBuff")

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(type=event_type, data=data, source="provider_detector"))
        except Exception:
            pass
