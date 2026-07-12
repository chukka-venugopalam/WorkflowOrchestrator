"""Vercel integration for the Workflow Orchestrator.

Provides functions to open the Vercel dashboard and
deployment URLs in the browser. Vercel is a cloud platform
for frontend deployments.
"""

from __future__ import annotations

import webbrowser

from config import config_manager
from modules.logger import logger


def open_dashboard() -> bool:
    """Open the Vercel dashboard in the default browser.

    Returns:
        bool: True if the dashboard URL was opened successfully.
    """
    url = config_manager.config.vercel_dashboard_url
    if not url:
        logger.warning("Vercel dashboard URL is not configured.")
        return False

    try:
        webbrowser.open(url)
        logger.info("Opened Vercel dashboard: %s", url)
        return True
    except Exception as exc:
        logger.error("Failed to open Vercel dashboard: %s", exc)
        return False


def open_deployment(deployment_url: str) -> bool:
    """Open a specific Vercel deployment URL.

    Args:
        deployment_url: The full URL of the deployed site.

    Returns:
        bool: True if the deployment URL was opened successfully.
    """
    if not deployment_url:
        logger.warning("No deployment URL provided.")
        return False

    try:
        webbrowser.open(deployment_url)
        logger.info("Opened Vercel deployment: %s", deployment_url)
        return True
    except Exception as exc:
        logger.error("Failed to open deployment URL: %s", exc)
        return False
