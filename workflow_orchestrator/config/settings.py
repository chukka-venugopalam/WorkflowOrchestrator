"""Configuration settings with built-in defaults.

Defines all configuration keys with their default values,
types, and validation rules.  This is the single source of
truth for what configuration the application supports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConfigDefaults:
    """Built-in default values for all configuration keys.

    These are the lowest-precedence values, used when no other
    configuration source provides a value.
    """

    # Browser
    brave_executable_path: str = ""
    browser_executable: str = ""

    # Editor
    vscode_executable_path: str = "code"

    # Project
    default_project_directory: str = ""

    # URLs
    github_repository_url: str = ""
    render_dashboard_url: str = ""
    vercel_dashboard_url: str = ""

    # Tools
    freebuff_command: str = ""

    # Profiles
    active_profile: str = "default"

    # Core settings
    state_dir: str = ".orchestrator/state"
    artifacts_dir: str = ".orchestrator/artifacts"
    reports_dir: str = "reports"
    logs_dir: str = "logs"
    plugins_dir: str = "plugins"

    # Logging
    log_level: str = "INFO"
    log_to_file: bool = True
    log_to_console: bool = True
    log_format: str = "json"

    # Scheduler
    scheduler_enabled: bool = False
    scheduler_max_instances: int = 3

    # Execution
    default_timeout: int = 60
    max_retries: int = 0
    retry_delay: float = 1.0

    # Advanced
    debug: bool = False
    verbose: bool = False


# Map of known config keys to their types (for validation)
KNOWN_CONFIG_KEYS: dict[str, type] = {
    # String keys
    "brave_executable_path": str,
    "browser_executable": str,
    "vscode_executable_path": str,
    "default_project_directory": str,
    "github_repository_url": str,
    "render_dashboard_url": str,
    "vercel_dashboard_url": str,
    "freebuff_command": str,
    "active_profile": str,
    "state_dir": str,
    "artifacts_dir": str,
    "reports_dir": str,
    "logs_dir": str,
    "plugins_dir": str,
    "log_level": str,
    "log_format": str,
    # Boolean keys
    "log_to_file": bool,
    "log_to_console": bool,
    "scheduler_enabled": bool,
    "debug": bool,
    "verbose": bool,
    # Integer keys
    "scheduler_max_instances": int,
    "default_timeout": int,
    "max_retries": int,
    # Float keys
    "retry_delay": float,
}


def get_default(key: str) -> Any:
    """Get the default value for a configuration key.

    Args:
        key: The configuration key.

    Returns:
        The default value, or None if not found.
    """
    return getattr(ConfigDefaults(), key, None)
