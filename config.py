"""Configuration management for the Workflow Orchestrator.

This module handles loading and accessing configuration values
from the JSON configuration file. All configurable paths and
URLs are stored externally to avoid hardcoding.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = DEFAULT_CONFIG_DIR
CONFIG_FILE = PROJECT_ROOT / "data" / "config.json"


@dataclass
class AppConfig:
    """Application configuration loaded from config.json.

    Attributes:
        brave_executable_path: Path to the Brave browser executable.
        vscode_executable_path: Path to the VS Code executable.
        default_project_directory: Default project directory to open.
        github_repository_url: URL of the GitHub repository.
        render_dashboard_url: URL of the Render dashboard.
        vercel_dashboard_url: URL of the Vercel dashboard.
        freebuff_command: Command to launch Freebuff.
        custom: Additional custom configuration key-value pairs.
    """

    brave_executable_path: str = ""
    vscode_executable_path: str = "code"
    default_project_directory: str = ""
    github_repository_url: str = ""
    render_dashboard_url: str = ""
    vercel_dashboard_url: str = ""
    freebuff_command: str = ""
    custom: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AppConfig:
        """Create an AppConfig instance from a dictionary.

        Args:
            data: Dictionary containing configuration values.

        Returns:
            AppConfig: Populated configuration instance.
        """
        known_keys = {
            "brave_executable_path",
            "vscode_executable_path",
            "default_project_directory",
            "github_repository_url",
            "render_dashboard_url",
            "vercel_dashboard_url",
            "freebuff_command",
        }

        known = {k: v for k, v in data.items() if k in known_keys}
        custom = {k: v for k, v in data.items() if k not in known_keys}

        return cls(**known, custom=custom)


class ConfigurationManager:
    """Manages loading, accessing, and saving application configuration.

    The configuration is loaded from a JSON file on disk. If the file
    does not exist, sensible defaults are used.
    """

    def __init__(self, config_path: Path = CONFIG_FILE) -> None:
        """Initialize the configuration manager.

        Args:
            config_path: Path to the JSON configuration file.
        """
        self._config_path = Path(config_path)
        self._config: AppConfig = self._load()

    def _load(self) -> AppConfig:
        """Load configuration from the JSON file.

        Returns:
            AppConfig: Loaded or default configuration.
        """
        if not self._config_path.exists():
            logger.warning(
                "Configuration file not found at %s. Using defaults.",
                self._config_path,
            )
            return AppConfig()

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
            logger.info("Configuration loaded from %s", self._config_path)
            return AppConfig.from_dict(data)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load configuration: %s", exc)
            return AppConfig()

    def save(self) -> None:
        """Save the current configuration to the JSON file."""
        data = {
            "brave_executable_path": self._config.brave_executable_path,
            "vscode_executable_path": self._config.vscode_executable_path,
            "default_project_directory": self._config.default_project_directory,
            "github_repository_url": self._config.github_repository_url,
            "render_dashboard_url": self._config.render_dashboard_url,
            "vercel_dashboard_url": self._config.vercel_dashboard_url,
            "freebuff_command": self._config.freebuff_command,
            **self._config.custom,
        }

        self._config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info("Configuration saved to %s", self._config_path)
        except OSError as exc:
            logger.error("Failed to save configuration: %s", exc)

    @property
    def config(self) -> AppConfig:
        """Get the current application configuration."""
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key.

        Args:
            key: The configuration key to look up.
            default: Default value if the key is not found.

        Returns:
            Any: The configuration value or default.
        """
        return getattr(self._config, key, self._config.custom.get(key, default))

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value and persist to disk.

        Args:
            key: The configuration key to set.
            value: The value to assign.
        """
        if hasattr(self._config, key):
            setattr(self._config, key, value)
        else:
            self._config.custom[key] = value
        self.save()

    def configure_interactive(self) -> None:
        """Launch an interactive configuration prompt in the terminal."""
        print("\n=== Configuration Setup ===\n")

        fields = [
            ("brave_executable_path", "Brave executable path", self._config.brave_executable_path),
            ("vscode_executable_path", "VS Code executable path", self._config.vscode_executable_path),
            ("default_project_directory", "Default project directory", self._config.default_project_directory),
            ("github_repository_url", "GitHub repository URL", self._config.github_repository_url),
            ("render_dashboard_url", "Render dashboard URL", self._config.render_dashboard_url),
            ("vercel_dashboard_url", "Vercel dashboard URL", self._config.vercel_dashboard_url),
            ("freebuff_command", "Freebuff command (e.g., 'freebuff' or full path)", self._config.freebuff_command),
        ]

        for key, label, current in fields:
            current_str = current if current else "(not set)"
            value = input(f"{label} [{current_str}]: ").strip()
            if value:
                self.set(key, value)

        print("\nConfiguration saved.\n")


# Module-level singleton
config_manager = ConfigurationManager()
