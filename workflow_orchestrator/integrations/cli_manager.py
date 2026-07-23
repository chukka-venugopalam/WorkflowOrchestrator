"""CLI Manager — detects installed CLI tools and runtimes.

Detects:
Claude Code, Codex CLI, GitHub CLI, Docker, Python, Node, Git, Playwright
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any, Optional

from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


@dataclass
class CliToolInfo:
    """Information about a detected CLI tool.

    Attributes:
        name: Tool name.
        command: CLI command to invoke.
        path: Path to the executable.
        version: Detected version string.
        available: Whether the tool is available.
    """

    name: str = ""
    command: str = ""
    path: str = ""
    version: str = ""
    available: bool = False


class CliManager:
    """Detects installed CLI tools and runtimes by scanning PATH.

    Usage:
        >>> mgr = CliManager()
        >>> tools = mgr.detect_all()
        >>> for t in tools:
        ...     print(f"{t.name}: {t.version}")
    """

    # Tools to detect: (name, command, version_flag)
    _TOOLS: list[tuple[str, str, str]] = [
        ("Claude Code", "claude", "--version"),
        ("Codex CLI", "codex", "--version"),
        ("GitHub CLI", "gh", "--version"),
        ("Docker", "docker", "--version"),
        ("Docker Compose", "docker-compose", "--version"),
        ("Python 3", "python3", "--version"),
        ("Python", "python", "--version"),
        ("Node.js", "node", "--version"),
        ("NPM", "npm", "--version"),
        ("Yarn", "yarn", "--version"),
        ("PNPM", "pnpm", "--version"),
        ("Git", "git", "--version"),
        ("Playwright", "playwright", "--version"),
        ("UV", "uv", "--version"),
        ("Poetry", "poetry", "--version"),
        ("Pip", "pip", "--version"),
        ("Rust", "rustc", "--version"),
        ("Cargo", "cargo", "--version"),
        ("Go", "go", "version"),
        ("Java", "java", "-version"),
        (".NET", "dotnet", "--version"),
        ("TypeScript", "tsc", "--version"),
        ("ESLint", "eslint", "--version"),
        ("Prettier", "prettier", "--version"),
        ("MCP", "mcp", "--version"),
        ("SSH", "ssh", "-V"),
        ("Curl", "curl", "--version"),
        ("Wget", "wget", "--version"),
        ("Make", "make", "--version"),
        ("CMake", "cmake", "--version"),
    ]

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the CLI Manager.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus

    def detect_all(self) -> list[CliToolInfo]:
        """Detect all installed CLI tools.

        Returns:
            List of CliToolInfo objects.
        """
        tools: list[CliToolInfo] = []
        for name, command, version_flag in self._TOOLS:
            info = self._detect_tool(name, command, version_flag)
            tools.append(info)
        return tools

    def detect_available(self) -> list[CliToolInfo]:
        """Detect only available CLI tools.

        Returns:
            List of available CliToolInfo objects.
        """
        return [t for t in self.detect_all() if t.available]

    def _detect_tool(self, name: str, command: str, version_flag: str) -> CliToolInfo:
        """Detect a specific CLI tool.

        Args:
            name: Tool name.
            command: CLI command.
            version_flag: Flag to get version.

        Returns:
            CliToolInfo for the tool.
        """
        exe_path = shutil.which(command)
        if not exe_path:
            return CliToolInfo(name=name, command=command, available=False)

        version = ""
        try:
            result = subprocess.run(
                [command] + version_flag.split(),
                capture_output=True, text=True, timeout=5,
            )
            version = (result.stdout or result.stderr).strip().split("\n")[0][:80]
        except Exception:
            pass

        return CliToolInfo(
            name=name,
            command=command,
            path=exe_path,
            version=version,
            available=True,
        )

    def find(self, command: str) -> CliToolInfo | None:
        """Find a CLI tool by command name.

        Args:
            command: The command to find.

        Returns:
            CliToolInfo if found, None otherwise.
        """
        exe_path = shutil.which(command)
        if not exe_path:
            return None
        return CliToolInfo(name=command, command=command, path=exe_path, available=True)

    def is_available(self, command: str) -> bool:
        """Check if a CLI command is available.

        Args:
            command: The command to check.

        Returns:
            True if available.
        """
        return shutil.which(command) is not None
