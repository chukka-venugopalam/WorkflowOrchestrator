"""Render.com integration for the Workflow Orchestrator.

Provides functions to open the Render dashboard and logs page
in the browser. Uses the standard library webbrowser module
for cross-platform compatibility.
"""

from __future__ import annotations

import webbrowser

from config import config_manager
from modules.logger import logger


def open_dashboard() -> bool:
    """Open the Render dashboard in the default browser.

    Returns:
        bool: True if the dashboard URL was opened successfully.
    """
    url = config_manager.config.render_dashboard_url
    if not url:
        logger.warning("Render dashboard URL is not configured.")
        return False

    try:
        webbrowser.open(url)
        logger.info("Opened Render dashboard: %s", url)
        return True
    except Exception as exc:
        logger.error("Failed to open Render dashboard: %s", exc)
        return False


def open_logs() -> bool:
    """Open the Render service logs page.

    Appends '/logs' to the configured Render dashboard URL.

    Returns:
        bool: True if the logs page was opened successfully.
    """
    url = config_manager.config.render_dashboard_url
    if not url:
        logger.warning("Render dashboard URL is not configured.")
        return False

    logs_url = url.rstrip("/") + "/logs"
    try:
        webbrowser.open(logs_url)
        logger.info("Opened Render logs: %s", logs_url)
        return True
    except Exception as exc:
        logger.error("Failed to open Render logs: %s", exc)
        return False
