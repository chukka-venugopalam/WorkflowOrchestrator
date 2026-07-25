"""Brave browser automation for the Workflow Orchestrator.

Provides functions to open the Brave browser with specific URLs,
including deployment pages and GitHub repositories.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from config import config_manager
from modules.logger import logger
from modules.terminal import run_command_async
from modules.utils import find_executable


def _get_brave_command() -> Optional[str]:
    """Resolve the Brave browser executable path.

    Checks the configuration first, then falls back to PATH lookup.

    Returns:
        Optional[str]: The Brave executable path, or None if not found.
    """
    config = config_manager.config
    if config.brave_executable_path:
        return config.brave_executable_path

    brave_cmd = find_executable("brave")
    if brave_cmd:
        return brave_cmd

    # Windows common installation paths
    windows_paths = [
        Path("C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"),
        Path("C:/Program Files (x86)/BraveSoftware/Brave-Browser/Application/brave.exe"),
    ]

    for path in windows_paths:
        if path.exists():
            return str(path)

    logger.error(
        "Brave browser not found. Set brave_executable_path in config."
    )
    return None


def open_url(url: str) -> bool:
    """Open a URL in Brave browser.

    Args:
        url: The fully qualified URL to open (e.g., 'https://example.com').

    Returns:
        bool: True if the browser was launched successfully.
    """
    brave = _get_brave_command()
    if not brave:
        return False

    try:
        run_command_async(f'"{brave}" "{url}"')
        logger.info("Opened Brave with URL: %s", url)
        return True
    except Exception as exc:
        logger.error("Failed to open Brave: %s", exc)
        return False


def open_github() -> bool:
    """Open the configured GitHub repository in Brave.

    Returns:
        bool: True if the page was opened successfully.
    """
    url = config_manager.config.github_repository_url
    if not url:
        logger.warning("GitHub repository URL is not configured.")
        return False
    return open_url(url)


def open_render() -> bool:
    """Open the configured Render dashboard in Brave.

    Returns:
        bool: True if the page was opened successfully.
    """
    url = config_manager.config.render_dashboard_url
    if not url:
        logger.warning("Render dashboard URL is not configured.")
        return False
    return open_url(url)


def open_render_logs() -> bool:
    """Open the Render logs page by appending '/logs' to the dashboard URL.

    Returns:
        bool: True if the page was opened successfully.
    """
    url = config_manager.config.render_dashboard_url
    if not url:
        logger.warning("Render dashboard URL is not configured.")
        return False
    logs_url = url.rstrip("/") + "/logs"
    return open_url(logs_url)


def open_vercel() -> bool:
    """Open the configured Vercel dashboard in Brave.

    Returns:
        bool: True if the page was opened successfully.
    """
    url = config_manager.config.vercel_dashboard_url
    if not url:
        logger.warning("Vercel dashboard URL is not configured.")
        return False
    return open_url(url)


def open_vercel_deployment(deployment_url: str) -> bool:
    """Open a specific Vercel deployment URL in Brave.

    Args:
        deployment_url: The deployment URL to open.

    Returns:
        bool: True if the page was opened successfully.
    """
    if not deployment_url:
        logger.warning("No deployment URL provided.")
        return False
    return open_url(deployment_url)
