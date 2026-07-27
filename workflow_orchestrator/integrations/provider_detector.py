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
            self._detect_antigravity,
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

    def _is_process_running(self, name_pattern: str) -> tuple[bool, str]:
        """Check if a process matching name_pattern is currently running on Windows/OS."""
        if sys.platform == "win32":
            try:
                res = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=3)
                if res.returncode == 0:
                    pattern_lower = name_pattern.lower()
                    for line in res.stdout.splitlines():
                        if pattern_lower in line.lower():
                            parts = line.split(",")
                            img_name = parts[0].strip('"') if parts else name_pattern
                            return True, f"Running Process '{img_name}'"
            except Exception:
                pass
        return False, ""

    def _detect_claude_desktop(self) -> DetectedProvider:
        """Detect Claude Desktop application across macOS and Windows."""
        # 1. Check running process
        running, proc_msg = self._is_process_running("claude")
        if running:
            return DetectedProvider(
                provider_id="anthropic.claude",
                name="Claude Desktop",
                version="detected",
                transport="desktop",
                path=proc_msg,
                detected_from=proc_msg,
                available=True,
                unavailable_reason="",
            )

        # 2. Check filesystem paths
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
        win_paths = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Claude",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Claude" / "Claude.exe",
            Path(os.environ.get("PROGRAMFILES", "")) / "Claude" / "Claude.exe",
            Path(os.environ.get("ProgramFiles(x86)", "")) / "Claude" / "Claude.exe",
        ]
        for wp in win_paths:
            if wp.exists():
                return DetectedProvider(
                    provider_id="anthropic.claude",
                    name="Claude Desktop",
                    version="detected",
                    transport="desktop",
                    path=str(wp),
                    detected_from="Windows Installation",
                    available=True,
                    unavailable_reason="",
                )
        return DetectedProvider(
            provider_id="anthropic.claude",
            name="Claude Desktop",
            available=False,
            unavailable_reason="Claude Desktop process or installation path not detected",
        )

    def _detect_claude_code(self) -> DetectedProvider:
        """Detect Claude Code CLI."""
        claude_path = shutil.which("claude")
        if not claude_path:
            npm_cmd = Path(os.environ.get("APPDATA", "")) / "npm" / "claude.cmd"
            if npm_cmd.exists():
                claude_path = str(npm_cmd)
        if claude_path:
            version = ""
            try:
                result = subprocess.run([claude_path, "--version"], capture_output=True, text=True, timeout=5)
                version = result.stdout.strip() or result.stderr.strip()
            except Exception:
                pass
            return DetectedProvider(
                provider_id="anthropic.claude",
                name="Claude Code",
                version=version or "detected",
                transport="cli",
                path=str(claude_path),
                detected_from="PATH/npm",
                available=True,
                unavailable_reason="",
            )
        return DetectedProvider(
            provider_id="anthropic.claude",
            name="Claude Code",
            available=False,
            unavailable_reason="'claude' executable not found on PATH or %APPDATA%\\npm",
        )

    def _detect_chatgpt_desktop(self) -> DetectedProvider:
        """Detect ChatGPT Desktop application."""
        # 1. Check running process
        running, proc_msg = self._is_process_running("chatgpt")
        if running:
            return DetectedProvider(
                provider_id="openai.chatgpt",
                name="ChatGPT Desktop",
                version="detected",
                transport="desktop",
                path=proc_msg,
                detected_from=proc_msg,
                available=True,
                unavailable_reason="",
            )

        # 2. Check filesystem paths
        mac_path = Path("/Applications/ChatGPT.app")
        if mac_path.exists():
            return DetectedProvider(
                provider_id="openai.chatgpt",
                name="ChatGPT Desktop",
                version="detected",
                transport="desktop",
                path=str(mac_path),
                detected_from="/Applications",
                available=True,
                unavailable_reason="",
            )
        win_paths = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "ChatGPT" / "ChatGPT.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "ChatGPT",
            Path(os.environ.get("PROGRAMFILES", "")) / "ChatGPT" / "ChatGPT.exe",
        ]
        for wp in win_paths:
            if wp.exists():
                return DetectedProvider(
                    provider_id="openai.chatgpt",
                    name="ChatGPT Desktop",
                    version="detected",
                    transport="desktop",
                    path=str(wp),
                    detected_from="Windows Installation",
                    available=True,
                    unavailable_reason="",
                )
        which_chatgpt = shutil.which("chatgpt")
        if which_chatgpt:
            return DetectedProvider(
                provider_id="openai.chatgpt",
                name="ChatGPT Desktop",
                version="detected",
                transport="desktop",
                path=which_chatgpt,
                detected_from="PATH",
                available=True,
                unavailable_reason="",
            )
        return DetectedProvider(
            provider_id="openai.chatgpt",
            name="ChatGPT Desktop",
            available=False,
            unavailable_reason="ChatGPT Desktop process or installation path not detected",
        )

    def _detect_gemini_cli(self) -> DetectedProvider:
        """Detect Gemini CLI or Gemini Web via Brave/Chrome browser."""
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
        # Check running web browsers (Brave, Chrome, Edge) for Gemini Web transport
        for b_proc in ["brave", "chrome", "msedge"]:
            running, proc_msg = self._is_process_running(b_proc)
            if running:
                return DetectedProvider(
                    provider_id="google.gemini",
                    name="Gemini (Web)",
                    version="web",
                    transport="browser",
                    path=proc_msg,
                    detected_from=f"Web Transport ({proc_msg})",
                    available=True,
                    unavailable_reason="",
                )
        # Check browser installation paths
        brave_path = Path(os.environ.get("LOCALAPPDATA", "")) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe"
        if brave_path.exists():
            return DetectedProvider(
                provider_id="google.gemini",
                name="Gemini (Web)",
                version="web",
                transport="browser",
                path=str(brave_path),
                detected_from="Brave Browser",
                available=True,
                unavailable_reason="",
            )
        return DetectedProvider(
            provider_id="google.gemini",
            name="Gemini CLI",
            available=False,
            unavailable_reason="'gemini' CLI or Brave/Chrome/Edge browser process not detected",
        )

    def _detect_cursor(self) -> DetectedProvider:
        """Detect Cursor editor across Windows and macOS."""
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
        win_paths = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "cursor" / "Cursor.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Cursor" / "Cursor.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "cursor",
        ]
        for wp in win_paths:
            if wp.exists():
                return DetectedProvider(
                    provider_id="cursor",
                    name="Cursor",
                    version="detected",
                    transport="desktop",
                    path=str(wp),
                    detected_from="Windows AppData",
                    available=True,
                    unavailable_reason="",
                )
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
            unavailable_reason="'cursor' executable or Cursor.exe not found in standard paths",
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
        """Detect GitHub Copilot extension across VS Code, VS Code Insiders, and Cursor."""
        ext_dirs = [
            Path.home() / ".vscode" / "extensions",
            Path.home() / ".vscode-insiders" / "extensions",
            Path.home() / ".cursor" / "extensions",
            Path(os.environ.get("USERPROFILE", "")) / ".vscode" / "extensions",
        ]
        for ext_dir in ext_dirs:
            if ext_dir.exists():
                for ext in ext_dir.glob("github.copilot-*"):
                    return DetectedProvider(
                        provider_id="github.copilot",
                        name="GitHub Copilot",
                        version="detected",
                        transport="desktop",
                        path=str(ext),
                        detected_from=f"{ext_dir.name} extensions",
                        available=True,
                        unavailable_reason="",
                    )
        return DetectedProvider(
            provider_id="github.copilot",
            name="GitHub Copilot",
            available=False,
            unavailable_reason="Extension directories (.vscode, .vscode-insiders, .cursor) have no github.copilot-* entry",
        )

    def _detect_continue(self) -> DetectedProvider:
        """Detect Continue.dev extension."""
        ext_dirs = [
            Path.home() / ".vscode" / "extensions",
            Path.home() / ".vscode-insiders" / "extensions",
            Path.home() / ".cursor" / "extensions",
        ]
        for ext_dir in ext_dirs:
            if ext_dir.exists():
                for ext in ext_dir.glob("continue.continue-*"):
                    return DetectedProvider(
                        provider_id="continue",
                        name="Continue",
                        version="detected",
                        transport="desktop",
                        path=str(ext),
                        detected_from=f"{ext_dir.name} extensions",
                        available=True,
                        unavailable_reason="",
                    )
        return DetectedProvider(
            provider_id="continue",
            name="Continue",
            available=False,
            unavailable_reason="Extension directories have no continue.continue-* entry",
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

    def _detect_antigravity(self) -> DetectedProvider:
        """Detect Antigravity AI agent tool."""
        agy_path = shutil.which("agy") or shutil.which("antigravity")
        antigravity_dir = Path.home() / ".gemini" / "antigravity"
        if agy_path or antigravity_dir.exists():
            return DetectedProvider(
                provider_id="antigravity",
                name="Antigravity",
                version="detected",
                transport="desktop",
                path=str(agy_path or antigravity_dir),
                detected_from="PATH/~/.gemini/antigravity",
                available=True,
                unavailable_reason="",
            )
        return DetectedProvider(
            provider_id="antigravity",
            name="Antigravity",
            available=False,
            unavailable_reason="'agy' executable or ~/.gemini/antigravity directory not found",
        )

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(type=event_type, data=data, source="provider_detector"))
        except Exception:
            pass
