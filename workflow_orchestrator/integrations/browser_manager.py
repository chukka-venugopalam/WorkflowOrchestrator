"""Browser Manager — detects installed browsers and their profiles.

Detects:
Chrome, Edge, Firefox, Brave, Arc, Opera
- Installed paths
- Profiles
- Running sessions
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
class BrowserInfo:
    """Information about an installed browser.

    Attributes:
        name: Browser name.
        executable_path: Path to the browser executable.
        profile_path: Path to the user profile directory.
        version: Detected version string.
        running: Whether the browser is currently running.
        profiles: List of detected profile names.
    """

    name: str = ""
    executable_path: str = ""
    profile_path: str = ""
    version: str = ""
    running: bool = False
    profiles: list[str] = field(default_factory=list)


class BrowserManager:
    """Detects installed browsers and their profiles.

    Scans standard installation paths and the system PATH for
    browser executables.

    Usage:
        >>> mgr = BrowserManager()
        >>> browsers = mgr.detect_all()
        >>> for b in browsers:
        ...     print(f"{b.name}: {b.executable_path}")
    """

    # Browser definitions: name -> (executable_names, profile_path_patterns)
    _BROWSERS: list[tuple[str, list[str], list[str]]] = [
        ("Chrome", ["google-chrome", "chrome", "google-chrome-stable"], [
            str(Path.home() / "Library" / "Application Support" / "Google" / "Chrome"),
            str(Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data"),
            str(Path.home() / ".config" / "google-chrome"),
        ]),
        ("Edge", ["microsoft-edge", "msedge"], [
            str(Path.home() / "Library" / "Application Support" / "Microsoft Edge"),
            str(Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data"),
            str(Path.home() / ".config" / "microsoft-edge"),
        ]),
        ("Firefox", ["firefox"], [
            str(Path.home() / "Library" / "Application Support" / "Firefox"),
            str(Path(os.environ.get("APPDATA", "")) / "Mozilla" / "Firefox"),
            str(Path.home() / ".mozilla" / "firefox"),
        ]),
        ("Brave", ["brave", "brave-browser"], [
            str(Path.home() / "Library" / "Application Support" / "BraveSoftware" / "Brave-Browser"),
            str(Path(os.environ.get("LOCALAPPDATA", "")) / "BraveSoftware" / "Brave-Browser" / "User Data"),
            str(Path.home() / ".config" / "brave"),
        ]),
        ("Arc", ["arc"], [
            str(Path.home() / "Library" / "Application Support" / "Arc"),
            str(Path(os.environ.get("LOCALAPPDATA", "")) / "Arc"),
        ]),
        ("Opera", ["opera"], [
            str(Path.home() / "Library" / "Application Support" / "com.operasoftware.Opera"),
            str(Path(os.environ.get("APPDATA", "")) / "Opera Software" / "Opera Stable"),
        ]),
    ]

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Browser Manager.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus

    def detect_all(self) -> list[BrowserInfo]:
        """Detect all installed browsers.

        Returns:
            List of BrowserInfo objects for detected browsers.
        """
        browsers: list[BrowserInfo] = []
        for name, exe_names, profile_paths in self._BROWSERS:
            info = self._detect_browser(name, exe_names, profile_paths)
            if info.executable_path or info.profile_path:
                browsers.append(info)
        return browsers

    def _detect_browser(
        self, name: str, exe_names: list[str], profile_paths: list[str]
    ) -> BrowserInfo:
        """Detect a specific browser.

        Args:
            name: Browser name.
            exe_names: Possible executable names.
            profile_paths: Possible profile directory paths.

        Returns:
            BrowserInfo for the detected browser.
        """
        info = BrowserInfo(name=name)

        # Find executable
        for exe_name in exe_names:
            exe_path = shutil.which(exe_name)
            if exe_path:
                info.executable_path = exe_path
                break

        # Find profile path
        for profile_path in profile_paths:
            if Path(profile_path).exists():
                info.profile_path = profile_path
                # Detect available profiles
                self._detect_profiles(info)
                break

        return info

    def _detect_profiles(self, info: BrowserInfo) -> None:
        """Detect browser profiles.

        Args:
            info: The browser info to update with profiles.
        """
        profile_dir = Path(info.profile_path)
        if info.name == "Chrome" and profile_dir.exists():
            for item in profile_dir.iterdir():
                if item.is_dir() and "Profile" in item.name:
                    info.profiles.append(item.name)
                elif item.is_dir() and item.name == "Default":
                    info.profiles.append("Default")

    def find_executable(self, name: str) -> str | None:
        """Find a browser executable by name.

        Args:
            name: Browser name (e.g., "Chrome", "Firefox").

        Returns:
            Path to executable, or None.
        """
        for browser_name, exe_names, _ in self._BROWSERS:
            if browser_name.lower() == name.lower():
                for exe_name in exe_names:
                    exe_path = shutil.which(exe_name)
                    if exe_path:
                        return exe_path
        return None
