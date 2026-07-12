"""Configuration management for the Workflow Orchestrator.

This module handles loading and accessing configuration values
from the JSON configuration file and YAML profile files.
All configurable paths and URLs are stored externally to avoid hardcoding.
Supports multiple configuration profiles (home, work, laptop) stored
as YAML files in the ``profiles/`` directory.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = DEFAULT_CONFIG_DIR
CONFIG_FILE = PROJECT_ROOT / "data" / "config.json"
PROFILES_DIR = PROJECT_ROOT / "profiles"


@dataclass
class AppConfig:
    """Application configuration loaded from config.json or a profile.

    Attributes:
        brave_executable_path: Path to the Brave browser executable.
        vscode_executable_path: Path to the VS Code executable.
        default_project_directory: Default project directory to open.
        github_repository_url: URL of the GitHub repository.
        render_dashboard_url: URL of the Render dashboard.
        vercel_dashboard_url: URL of the Vercel dashboard.
        freebuff_command: Command to launch Freebuff.
        active_profile: Name of the currently active configuration profile.
        custom: Additional custom configuration key-value pairs.
    """

    brave_executable_path: str = ""
    vscode_executable_path: str = "code"
    default_project_directory: str = ""
    github_repository_url: str = ""
    render_dashboard_url: str = ""
    vercel_dashboard_url: str = ""
    freebuff_command: str = ""
    active_profile: str = "default"
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
            "active_profile",
        }

        known = {k: v for k, v in data.items() if k in known_keys}
        custom = {k: v for k, v in data.items() if k not in known_keys}

        return cls(**known, custom=custom)


class ConfigurationManager:
    """Manages loading, accessing, and saving application configuration.

    Supports multiple configuration profiles stored as YAML files
    in the ``profiles/`` directory. The base config.json holds the
    active profile name and any machine-specific overrides.
    """

    def __init__(self, config_path: Path = CONFIG_FILE) -> None:
        """Initialize the configuration manager.

        Args:
            config_path: Path to the JSON configuration file.
        """
        self._config_path = Path(config_path)
        self._profiles_dir = PROFILES_DIR
        self._config: AppConfig = self._load()

    def _load(self) -> AppConfig:
        """Load configuration from the JSON file and the active profile.

        Returns:
            AppConfig: Merged configuration.
        """
        # Load base config
        base = self._load_base_config()

        # Try to load the active profile and merge it
        profile_name = base.active_profile or "default"
        profile = self._load_profile(profile_name)
        merged = self._merge_profile(base, profile)

        return merged

    def _load_base_config(self) -> AppConfig:
        """Load base configuration from config.json."""
        if not self._config_path.exists():
            logger.warning(
                "Configuration file not found at %s. Using defaults.",
                self._config_path,
            )
            return AppConfig()

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
            logger.info("Base configuration loaded from %s", self._config_path)
            return AppConfig.from_dict(data)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load configuration: %s", exc)
            return AppConfig()

    def _load_profile(self, profile_name: str) -> dict[str, Any]:
        """Load a configuration profile from the profiles directory.

        Args:
            profile_name: Name of the profile (without .yaml extension).

        Returns:
            dict: Profile configuration values.
        """
        try:
            from workflow_orchestrator.models import ProfileConfig

            profile_path = self._profiles_dir / f"{profile_name}.yaml"
            if not profile_path.exists():
                # Try default profile
                default_path = self._profiles_dir / "default.yaml"
                if default_path.exists():
                    profile = ProfileConfig.from_yaml(default_path)
                    return profile.to_app_config_dict()
                return {}

            profile = ProfileConfig.from_yaml(profile_path)
            return profile.to_app_config_dict()
        except ImportError:
            logger.warning(
                "Could not import models module for profile '%s'. "
                "This may happen during early initialization.",
                profile_name,
            )
            return {}
        except Exception as exc:
            logger.error("Failed to load profile '%s': %s", profile_name, exc)
            return {}

    def _merge_profile(self, base: AppConfig, profile: dict[str, Any]) -> AppConfig:
        """Merge profile values into the base config.

        Profile values override base values only when the profile
        value is non-empty and non-default.

        Args:
            base: The base AppConfig.
            profile: Profile configuration dictionary.

        Returns:
            AppConfig: Merged configuration.
        """
        import copy

        merged = copy.deepcopy(base)

        for key in (
            "brave_executable_path",
            "vscode_executable_path",
            "default_project_directory",
            "github_repository_url",
            "render_dashboard_url",
            "vercel_dashboard_url",
            "freebuff_command",
        ):
            profile_val = profile.get(key)
            if profile_val:
                setattr(merged, key, profile_val)

        # Merge custom keys
        profile_custom = {k: v for k, v in profile.items() if k not in (
            "brave_executable_path", "vscode_executable_path",
            "default_project_directory", "github_repository_url",
            "render_dashboard_url", "vercel_dashboard_url",
            "freebuff_command", "name", "description", "env",
        )}
        merged.custom.update(profile_custom)

        return merged

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
            "active_profile": self._config.active_profile,
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

    @property
    def profiles_dir(self) -> Path:
        """Get the profiles directory path."""
        return self._profiles_dir

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

    def list_profiles(self) -> list[str]:
        """List available configuration profiles.

        Returns:
            list[str]: Sorted list of profile names (without extension).
        """
        if not self._profiles_dir.exists():
            return ["default"]

        profiles = sorted(
            p.stem for p in self._profiles_dir.glob("*.yaml") if p.stem != "default" or True
        )
        return profiles if profiles else ["default"]

    def switch_profile(self, profile_name: str) -> bool:
        """Switch the active configuration profile.

        Args:
            profile_name: Name of the profile to activate.

        Returns:
            bool: True if the profile was switched successfully.
        """
        profile_path = self._profiles_dir / f"{profile_name}.yaml"
        if not profile_path.exists():
            logger.error("Profile '%s' not found at %s", profile_name, profile_path)
            return False

        self._config.active_profile = profile_name
        self.save()

        # Reload config with the new profile
        self._config = self._load()

        logger.info("Switched to profile '%s'", profile_name)
        return True

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
            ("active_profile", "Active profile name", self._config.active_profile),
        ]

        for key, label, current in fields:
            current_str = current if current else "(not set)"
            value = input(f"{label} [{current_str}]: ").strip()
            if value:
                self.set(key, value)

        print("\nConfiguration saved.\n")


# Module-level singleton
config_manager = ConfigurationManager()
