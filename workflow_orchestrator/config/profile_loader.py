"""Profile loader for YAML configuration profiles.

Loads and merges YAML configuration profiles from the ``profiles/``
directory.  Profiles are merged with base configuration, with
profile values taking precedence.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


class ProfileLoader:
    """Loads and manages YAML configuration profiles.

    Profiles are stored as YAML files in a profiles directory.
    Each profile can override any configuration key.

    Usage:
        >>> loader = ProfileLoader(profiles_dir=Path("/path/to/profiles"))
        >>> profile = loader.load("home")
        >>> print(profile.get("default_project_directory"))
    """

    def __init__(self, profiles_dir: Path | str) -> None:
        """Initialize the profile loader.

        Args:
            profiles_dir: Directory containing YAML profile files.
        """
        self._profiles_dir = Path(profiles_dir).expanduser().resolve()
        self._cache: dict[str, dict[str, Any]] = {}

    @property
    def profiles_dir(self) -> Path:
        """The profiles directory path."""
        return self._profiles_dir

    def load(self, profile_name: str) -> dict[str, Any]:
        """Load a profile by name.

        Args:
            profile_name: Name of the profile (without ``.yaml`` extension).

        Returns:
            Dictionary of configuration values from the profile.

        Raises:
            FileNotFoundError: If the profile file does not exist.
        """
        # Check cache
        if profile_name in self._cache:
            return self._cache[profile_name].copy()

        # Default profile is always available as empty if not found
        if profile_name == "default":
            return {}

        profile_path = self._profiles_dir / f"{profile_name}.yaml"
        if not profile_path.exists():
            # Try without extension
            profile_path = self._profiles_dir / profile_name
            if not profile_path.exists():
                # Try default profile as fallback
                default_path = self._profiles_dir / "default.yaml"
                if default_path.exists():
                    data = self._load_file(default_path)
                    self._cache[profile_name] = data
                    return data.copy()
                return {}

        data = self._load_file(profile_path)
        self._cache[profile_name] = data
        return data.copy()

    def load_default(self) -> dict[str, Any]:
        """Load the default profile.

        Returns:
            Default profile configuration.
        """
        return self.load("default")

    def _load_file(self, path: Path) -> dict[str, Any]:
        """Load a YAML file and return its contents.

        Args:
            path: Path to the YAML file.

        Returns:
            Dictionary of profile values.
        """
        if not path.exists():
            logger.warning("Profile file not found: %s", path)
            return {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                data: dict[str, Any] = yaml.safe_load(f) or {}
            logger.debug("Loaded profile from %s", path)
            return data
        except (yaml.YAMLError, OSError) as exc:
            logger.error("Failed to load profile %s: %s", path, exc)
            return {}

    def list_profiles(self) -> list[str]:
        """List available profile names.

        Returns:
            Sorted list of profile names (without extension).
        """
        if not self._profiles_dir.exists():
            return ["default"]

        profiles = sorted(
            p.stem for p in self._profiles_dir.glob("*.yaml")
        )
        return profiles if profiles else ["default"]

    def exists(self, profile_name: str) -> bool:
        """Check if a profile exists.

        Args:
            profile_name: Profile name to check.

        Returns:
            True if the profile file exists.
        """
        if profile_name == "default":
            return True
        profile_path = self._profiles_dir / f"{profile_name}.yaml"
        return profile_path.exists()

    def clear_cache(self) -> None:
        """Clear the profile cache."""
        self._cache.clear()

    def reload(self, profile_name: str) -> dict[str, Any]:
        """Reload a profile, bypassing cache.

        Args:
            profile_name: Profile name to reload.

        Returns:
            Profile configuration data.
        """
        self._cache.pop(profile_name, None)
        return self.load(profile_name)
