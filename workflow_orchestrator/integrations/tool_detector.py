"""Tool Detector — detects installed developer tools.

Detects:
VS Code, Cursor, Chrome, Firefox, Docker, Git, Playwright, Terminal, SSH, MCP
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


@dataclass
class ToolInfo:
    """Information about a detected developer tool.

    Attributes:
        name: Tool name.
        category: Tool category (editor, browser, runtime, etc.).
        command: CLI command (if applicable).
        path: Path to the tool.
        version: Detected version.
        available: Whether the tool is available.
    """

    name: str = ""
    category: str = ""
    command: str = ""
    path: str = ""
    version: str = ""
    available: bool = False


class ToolDetector:
    """Detects installed developer tools.

    Scans PATH, standard installation paths, and configuration
    directories for common developer tools.

    Usage:
        >>> detector = ToolDetector()
        >>> tools = detector.detect_all()
        >>> for t in tools:
        ...     print(f"{t.name}: {t.category}")
    """

    # Tool definitions: (name, category, command, check_paths)
    _TOOLS: list[tuple[str, str, str, list[str]]] = [
        ("VS Code", "editor", "code", [
            "/Applications/Visual Studio Code.app",
        ]),
        ("Cursor", "editor", "cursor", [
            "/Applications/Cursor.app",
        ]),
        ("Chrome", "browser", "google-chrome", [
            "/Applications/Google Chrome.app",
        ]),
        ("Firefox", "browser", "firefox", [
            "/Applications/Firefox.app",
        ]),
        ("Brave", "browser", "brave", [
            "/Applications/Brave Browser.app",
        ]),
        ("Docker", "runtime", "docker", []),
        ("Git", "vcs", "git", []),
        ("SSH", "network", "ssh", []),
        ("Curl", "network", "curl", []),
        ("Node.js", "runtime", "node", []),
        ("Python", "runtime", "python3", []),
        ("GitHub CLI", "vcs", "gh", []),
        ("Make", "build", "make", []),
        ("Playwright", "test", "playwright", []),
        ("NPM", "package_manager", "npm", []),
        ("Yarn", "package_manager", "yarn", []),
        ("PNPM", "package_manager", "pnpm", []),
        ("UV", "package_manager", "uv", []),
        ("Poetry", "package_manager", "poetry", []),
        ("Pip", "package_manager", "pip", []),
    ]

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Tool Detector.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus

    def detect_all(self) -> list[ToolInfo]:
        """Detect all installed developer tools.

        Returns:
            List of ToolInfo objects.
        """
        tools: list[ToolInfo] = []
        for name, category, command, check_paths in self._TOOLS:
            info = self._detect_tool(name, category, command, check_paths)
            tools.append(info)
        return tools

    def detect_available(self) -> list[ToolInfo]:
        """Detect only available tools.

        Returns:
            List of available ToolInfo objects.
        """
        return [t for t in self.detect_all() if t.available]

    def _detect_tool(
        self, name: str, category: str, command: str, check_paths: list[str],
    ) -> ToolInfo:
        """Detect a specific tool.

        Args:
            name: Tool name.
            category: Tool category.
            command: CLI command.
            check_paths: Additional installation paths to check.

        Returns:
            ToolInfo for the detected tool.
        """
        # Check PATH
        exe_path = shutil.which(command)
        if exe_path:
            return ToolInfo(
                name=name, category=category, command=command,
                path=exe_path, available=True,
            )

        # Check paths
        for check_path in check_paths:
            if Path(check_path).exists():
                return ToolInfo(
                    name=name, category=category, command=command,
                    path=check_path, available=True,
                )

        return ToolInfo(name=name, category=category, command=command)
