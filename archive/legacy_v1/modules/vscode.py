"""VS Code integration for the Workflow Orchestrator.

Provides functions to open Visual Studio Code with specific
projects and files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from config import config_manager
from modules.logger import logger
from modules.terminal import run_command_async
from modules.utils import find_executable


def _get_vscode_command() -> Optional[str]:
    """Resolve the VS Code executable path.

    Checks the configuration first, then falls back to PATH lookup.
    On Windows, 'code' is typically available if VS Code was installed
    with the 'Add to PATH' option.

    Returns:
        Optional[str]: The VS Code command, or None if not found.
    """
    config = config_manager.config
    if config.vscode_executable_path:
        return config.vscode_executable_path

    code_cmd = find_executable("code")
    if code_cmd:
        return code_cmd

    logger.error(
        "VS Code not found. Set vscode_executable_path in config."
    )
    return None


def open_vscode(project_path: Optional[Path] = None) -> bool:
    """Open VS Code, optionally with a specific project directory.

    Args:
        project_path: Path to the project directory to open.
            If None, opens VS Code without a specific project.

    Returns:
        bool: True if VS Code was launched successfully.
    """
    cmd = _get_vscode_command()
    if not cmd:
        return False

    if project_path:
        resolved = project_path.expanduser().resolve()
        if not resolved.exists():
            logger.warning("Project directory does not exist: %s", resolved)
    else:
        resolved = None

    try:
        if resolved:
            run_command_async(f'"{cmd}" "{resolved}"')
            logger.info("Opened VS Code with project: %s", resolved)
        else:
            run_command_async(f'"{cmd}"')
            logger.info("Opened VS Code.")
        return True
    except Exception as exc:
        logger.error("Failed to open VS Code: %s", exc)
        return False


def open_in_vscode(file_path: Path) -> bool:
    """Open a specific file in VS Code.

    Args:
        file_path: Path to the file to open in VS Code.

    Returns:
        bool: True if the file was opened successfully.
    """
    cmd = _get_vscode_command()
    if not cmd:
        return False

    resolved = file_path.expanduser().resolve()
    if not resolved.exists():
        logger.warning("File does not exist: %s", resolved)
        return False

    try:
        run_command_async(f'"{cmd}" "{resolved}"')
        logger.info("Opened file in VS Code: %s", resolved)
        return True
    except Exception as exc:
        logger.error("Failed to open file in VS Code: %s", exc)
        return False
