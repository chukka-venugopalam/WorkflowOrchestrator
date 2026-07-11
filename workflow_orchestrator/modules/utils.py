"""Common utility functions for the Workflow Orchestrator.

Provides reusable helpers used across multiple modules,
such as platform detection, path resolution, and input validation.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional


def detect_platform() -> str:
    """Detect the current operating system.

    Returns:
        str: One of 'windows', 'darwin', or 'linux'.
    """
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    if system == "darwin":
        return "darwin"
    return "linux"


def find_executable(name: str) -> Optional[str]:
    """Find an executable in the system PATH.

    Args:
        name: Name of the executable (e.g., 'brave', 'code').

    Returns:
        Optional[str]: Full path to the executable, or None if not found.
    """
    resolved = shutil.which(name)
    if resolved:
        return resolved
    return None


def resolve_path(path_str: str) -> Path:
    """Resolve a path string to an absolute Path, expanding ~ and env vars.

    Args:
        path_str: Path string that may contain ~ or environment variables.

    Returns:
        Path: Resolved absolute path.
    """
    return Path(path_str).expanduser().resolve()


def open_file_in_explorer(path: Path) -> bool:
    """Open a file or directory in the system file manager.

    Args:
        path: Path to the file or directory to open.

    Returns:
        bool: True if the command was launched successfully.
    """
    system = detect_platform()

    try:
        if system == "windows":
            subprocess.Popen(["explorer", str(path)], shell=True)
        elif system == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return True
    except (OSError, subprocess.SubprocessError) as exc:
        from modules.logger import logger
        logger.error("Failed to open file in explorer: %s", exc)
        return False


def truncate_text(text: str, max_length: int = 80) -> str:
    """Truncate text to a maximum length with an ellipsis.

    Args:
        text: The text to truncate.
        max_length: Maximum character length before truncation.

    Returns:
        str: Truncated text with '...' appended if needed.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename.

    Replaces characters that are invalid in filenames with underscores.

    Args:
        name: The raw string to sanitize.

    Returns:
        str: Sanitized filename-safe string.
    """
    invalid_chars = r'<>:"/\|?*'
    sanitized = "".join("_" if c in invalid_chars else c for c in name)
    return sanitized.strip().replace(" ", "_") or "untitled"
