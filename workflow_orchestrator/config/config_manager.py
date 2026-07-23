"""Unified configuration manager for the Workflow Orchestrator.

Merges the two previous ``config.py`` implementations into a single
authoritative configuration manager that supports:
- JSON config files (``data/config.json``)
- YAML profile files (``profiles/*.yaml``)
- Environment variable overrides
- Profile merging and validation
- Configuration caching
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.config.settings import ConfigDefaults, KNOWN_CONFIG_KEYS, get_default
from workflow_orchestrator.config.validators import validate_key, validate_profile_name
from workflow_orchestrator.config.profile_loader import ProfileLoader

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = DEFAULT_CONFIG_DIR
CONFIG_FILE = PROJECT_ROOT / "data" / "config.json"
PROFILES_DIR = PROJECT_ROOT / "profiles"
ENV_PREFIX = "WO_"


@dataclass
class AppConfig:
    """Application configuration with all supported keys.

    This is the authoritative configuration data class.  It includes
    all keys from both previous implementations plus new keys added
    by the architecture.
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

    # Profile management
    active_profile: str = "default"

    # Core paths
    state_dir: str = ""
    artifacts_dir: str = ""
    logs_dir: str = ""

    # Logging
    log_level: str = "INFO"
    log_to_file: bool = True
    log_to_console: bool = True

    # Execution
    default_timeout: int = 60
    max_retries: int = 0
    retry_delay: float = 1.0

    # Scheduler
    scheduler_enabled: bool = False
    scheduler_max_instances: int = 3

    # Debug
    debug: bool = False
    verbose: bool = False

    # Custom keys
    custom: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppConfig:
        """Create an AppConfig instance from a dictionary.

        Args:
            data: Dictionary containing configuration values.

        Returns:
            AppConfig: Populated configuration instance.
        """
        known_keys = set(KNOWN_CONFIG_KEYS.keys())
        known = {}
        custom = {}

        for k, v in data.items():
            if k in known_keys:
                expected_type = KNOWN_CONFIG_KEYS.get(k)
                if expected_type and not isinstance(v, expected_type):
                    try:
                        if expected_type == bool and isinstance(v, str):
                            v = v.lower() in ("true", "1", "yes")
                        elif expected_type == int:
                            v = int(v)
                        elif expected_type == float:
                            v = float(v)
                    except (ValueError, TypeError):
                        v = get_default(k)
                known[k] = v
            else:
                custom[k] = v

        return cls(**known, custom=custom)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a flat dictionary."""
        result: dict[str, Any] = {
            "brave_executable_path": self.brave_executable_path,
            "vscode_executable_path": self.vscode_executable_path,
            "default_project_directory": self.default_project_directory,
            "github_repository_url": self.github_repository_url,
            "render_dashboard_url": self.render_dashboard_url,
            "vercel_dashboard_url": self.vercel_dashboard_url,
            "freebuff_command": self.freebuff_command,
            "active_profile": self.active_profile,
            "log_level": self.log_level,
            "log_to_file": self.log_to_file,
            "log_to_console": self.log_to_console,
            "default_timeout": self.default_timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "scheduler_enabled": self.scheduler_enabled,
            "debug": self.debug,
            "verbose": self.verbose,
            **self.custom,
        }
        return {k: v for k, v in result.items() if v}


class ConfigurationManager:
    """Unified configuration manager for loading, accessing, and saving config.

    Merges configuration from multiple sources with precedence:
    Built-in defaults < Base JSON config < Profile config < Environment variables

    This replaces both the root ``config.py`` and ``workflow_orchestrator/config.py``
    implementations.
    """

    def __init__(
        self,
        config_path: Path | str = CONFIG_FILE,
        profiles_dir: Path | str = PROFILES_DIR,
        env_prefix: str = ENV_PREFIX,
    ) -> None:
        """Initialize the configuration manager.

        Args:
            config_path: Path to the JSON configuration file.
            profiles_dir: Directory containing YAML profile files.
            env_prefix: Prefix for environment variable overrides.
        """
        self._config_path = Path(config_path)
        self._profiles_dir = Path(profiles_dir)
        self._env_prefix = env_prefix
        self._profile_loader = ProfileLoader(self._profiles_dir)
        self._config: AppConfig = self._load()
        self._cache: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self) -> AppConfig:
        """Load and merge configuration from all sources.

        Precedence (lowest to highest):
            1. Built-in defaults
            2. Base JSON config file
            3. Active profile YAML
            4. Environment variables

        Returns:
            Merged AppConfig.
        """
        # 1. Start with defaults
        config = AppConfig()

        # 2. Load base JSON config
        base = self._load_base_config()

        # 3. Load and merge active profile
        profile_name = base.active_profile or "default"
        profile_data = self._load_profile(profile_name)

        # Merge: base overrides defaults, profile overrides base
        merged_dict = self._merge(base.to_dict(), profile_data)

        # 4. Apply environment variable overrides
        env_overrides = self._load_env_overrides()
        merged_dict = self._merge(merged_dict, env_overrides)

        # 5. Create config from merged dict
        config = AppConfig.from_dict(merged_dict)
        return config

    def _load_base_config(self) -> AppConfig:
        """Load base configuration from config.json."""
        if not self._config_path.exists():
            logger.debug("Config file not found at %s, using defaults", self._config_path)
            return AppConfig()

        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
            return AppConfig.from_dict(data)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load config: %s", exc)
            return AppConfig()

    def _load_profile(self, profile_name: str) -> dict[str, Any]:
        """Load a profile's configuration values.

        Args:
            profile_name: Name of the profile.

        Returns:
            Profile configuration dictionary.
        """
        try:
            return self._profile_loader.load(profile_name)
        except Exception as exc:
            logger.warning("Failed to load profile '%s': %s", profile_name, exc)
            return {}

    def _load_env_overrides(self) -> dict[str, Any]:
        """Load configuration from environment variables.

        Environment variables with the configured prefix (default ``WO_``)
        override configuration values.  The env var name is the config key
        in UPPER_SNAKE_CASE (e.g., ``WO_BRAVE_EXECUTABLE_PATH``).

        Returns:
            Dictionary of environment variable overrides.
        """
        overrides: dict[str, Any] = {}
        for key in KNOWN_CONFIG_KEYS:
            env_key = f"{self._env_prefix}{key.upper()}"
            env_value = os.environ.get(env_key)
            if env_value is not None:
                expected_type = KNOWN_CONFIG_KEYS[key]
                try:
                    if expected_type == bool:
                        overrides[key] = env_value.lower() in ("true", "1", "yes")
                    elif expected_type == int:
                        overrides[key] = int(env_value)
                    elif expected_type == float:
                        overrides[key] = float(env_value)
                    else:
                        overrides[key] = env_value
                except (ValueError, TypeError):
                    logger.warning("Invalid env var %s = '%s', expected %s", env_key, env_value, expected_type.__name__)

        if overrides:
            logger.debug("Loaded %d environment variable overrides", len(overrides))

        return overrides

    @staticmethod
    def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Merge two configuration dictionaries.

        Args:
            base: Base configuration.
            override: Override configuration (takes precedence).

        Returns:
            Merged dictionary.
        """
        merged = {**base}
        for key, value in override.items():
            if value is not None and value != "":
                merged[key] = value
        return merged

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Save the current configuration to config.json.

        Only saves known keys and custom keys to the JSON file.
        Profile overrides and env vars are not persisted.
        """
        data = self._config.to_dict()
        self._config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.debug("Configuration saved to %s", self._config_path)
        except OSError as exc:
            logger.error("Failed to save configuration: %s", exc)

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    @property
    def config(self) -> AppConfig:
        """Get the current merged configuration."""
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key.

        Args:
            key: The configuration key.
            default: Default value if not found.

        Returns:
            The configuration value.
        """
        return getattr(self._config, key, self._config.custom.get(key, default))

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value and persist.

        Args:
            key: The configuration key.
            value: The value to set.
        """
        if key in KNOWN_CONFIG_KEYS:
            setattr(self._config, key, value)
        else:
            self._config.custom[key] = value
        self.save()

    def reload(self) -> None:
        """Reload configuration from all sources."""
        self._cache.clear()
        self._config = self._load()
        logger.info("Configuration reloaded")

    # ------------------------------------------------------------------
    # Profile management
    # ------------------------------------------------------------------

    def list_profiles(self) -> list[str]:
        """List available configuration profiles.

        Returns:
            Sorted list of profile names.
        """
        return self._profile_loader.list_profiles()

    def switch_profile(self, profile_name: str) -> bool:
        """Switch the active profile.

        Args:
            profile_name: Profile name to activate.

        Returns:
            True if successful.
        """
        if not self._profile_loader.exists(profile_name):
            logger.error("Profile '%s' not found", profile_name)
            return False

        self._config.active_profile = profile_name
        self.save()

        # Reload with new profile
        self._config = self._load()
        logger.info("Switched to profile '%s'", profile_name)
        return True

    def get_active_profile(self) -> str:
        """Get the active profile name.

        Returns:
            The active profile name.
        """
        return self._config.active_profile

    # ------------------------------------------------------------------
    # Interactive configuration
    # ------------------------------------------------------------------

    def configure_interactive(self) -> None:
        """Launch an interactive configuration prompt."""
        print("\n=== Configuration Setup ===\n")

        fields = [
            ("brave_executable_path", "Brave executable path"),
            ("vscode_executable_path", "VS Code executable path"),
            ("default_project_directory", "Default project directory"),
            ("github_repository_url", "GitHub repository URL"),
            ("render_dashboard_url", "Render dashboard URL"),
            ("vercel_dashboard_url", "Vercel dashboard URL"),
            ("freebuff_command", "Freebuff command (e.g., 'freebuff' or full path)"),
            ("active_profile", "Active profile name"),
            ("log_level", "Log level (DEBUG, INFO, WARNING, ERROR)"),
            ("default_timeout", "Default timeout in seconds"),
            ("max_retries", "Max retries on failure"),
        ]

        for key, label in fields:
            current = self.get(key)
            current_str = str(current) if current else "(not set)"
            try:
                value = input(f"{label} [{current_str}]: ").strip()
                if value:
                    self.set(key, value)
            except (EOFError, KeyboardInterrupt):
                print("\nConfiguration cancelled.")
                return

        print("\nConfiguration saved.\n")


# ---------------------------------------------------------------------------
# Module-level singleton and factory
# ---------------------------------------------------------------------------

# Module-level singleton for backward compatibility
_config_manager_instance: ConfigurationManager | None = None


def create_config_manager(
    config_path: Path | str | None = None,
    profiles_dir: Path | str | None = None,
    env_prefix: str = ENV_PREFIX,
) -> ConfigurationManager:
    """Create a new ConfigurationManager.

    Args:
        config_path: Path to the JSON config file.
        profiles_dir: Directory containing YAML profiles.
        env_prefix: Prefix for env var overrides.

    Returns:
        A new ConfigurationManager instance.
    """
    return ConfigurationManager(
        config_path=config_path or CONFIG_FILE,
        profiles_dir=profiles_dir or PROFILES_DIR,
        env_prefix=env_prefix,
    )


def get_config_manager() -> ConfigurationManager:
    """Get or create the module-level singleton ConfigurationManager.

    Returns:
        The shared ConfigurationManager instance.
    """
    global _config_manager_instance
    if _config_manager_instance is None:
        _config_manager_instance = create_config_manager()
    return _config_manager_instance


# Module-level singleton (backward compatible with existing import patterns)
config_manager = get_config_manager()
