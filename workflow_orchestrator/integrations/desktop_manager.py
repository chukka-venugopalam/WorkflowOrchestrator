"""Desktop Manager — detects installed desktop applications relevant to development.

Detects:
Claude Desktop, Cursor, VS Code, GitHub Desktop, Continue
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


@dataclass
class DesktopAppInfo:
    """Information about a detected desktop application.

    Attributes:
        name: Application name.
        executable_path: Path to the application executable.
        bundle_id: macOS bundle identifier.
        version: Detected version.
        running: Whether the application is currently running.
    """

    name: str = ""
    executable_path: str = ""
    bundle_id: str = ""
    version: str = ""
    running: bool = False


class DesktopManager:
    """Detects installed development desktop applications.

    Scans standard installation paths and PATH for desktop apps.

    Usage:
        >>> mgr = DesktopManager()
        >>> apps = mgr.detect_all()
        >>> for app in apps:
        ...     print(f"{app.name}: {app.executable_path}")
    """

    # Known desktop apps to detect
    _KNOWN_APPS: list[dict[str, Any]] = [
        {
            "name": "Claude Desktop",
            "mac_path": "/Applications/Claude.app",
            "win_path": os.environ.get("LOCALAPPDATA", "") + "/Claude/Claude.exe",
            "executable": "",
        },
        {
            "name": "Cursor",
            "mac_path": "/Applications/Cursor.app",
            "win_path": os.environ.get("LOCALAPPDATA", "") + "/Programs/Cursor/Cursor.exe",
            "executable": "cursor",
        },
        {
            "name": "VS Code",
            "mac_path": "/Applications/Visual Studio Code.app",
            "win_path": os.environ.get("LOCALAPPDATA", "") + "/Programs/Microsoft VS Code/Code.exe",
            "executable": "code",
        },
        {
            "name": "GitHub Desktop",
            "mac_path": "/Applications/GitHub Desktop.app",
            "win_path": os.environ.get("LOCALAPPDATA", "") + "/GitHubDesktop/GitHubDesktop.exe",
            "executable": "github",
        },
        {
            "name": "Continue",
            "mac_path": "",
            "win_path": "",
            "executable": "continue",
        },
    ]

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Desktop Manager.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus

    def detect_all(self) -> list[DesktopAppInfo]:
        """Detect all installed desktop applications.

        Returns:
            List of DesktopAppInfo objects.
        """
        apps: list[DesktopAppInfo] = []
        for app_def in self._KNOWN_APPS:
            info = self._detect_app(app_def)
            if info.executable_path or info.name:
                apps.append(info)
        return apps

    def _detect_app(self, app_def: dict[str, Any]) -> DesktopAppInfo:
        """Detect a specific desktop application.

        Args:
            app_def: Application definition dict.

        Returns:
            DesktopAppInfo for the detected application.
        """
        info = DesktopAppInfo(name=app_def["name"])

        # Check macOS path
        mac_path = app_def.get("mac_path", "")
        if mac_path and Path(mac_path).exists():
            info.executable_path = mac_path
            return info

        # Check Windows path
        win_path = app_def.get("win_path", "")
        if win_path and Path(win_path).exists():
            info.executable_path = win_path
            return info

        # Check PATH
        executable = app_def.get("executable", "")
        if executable:
            exe_path = shutil.which(executable)
            if exe_path:
                info.executable_path = exe_path
                return info

        return info
