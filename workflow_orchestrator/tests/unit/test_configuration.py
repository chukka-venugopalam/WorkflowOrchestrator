"""Unit tests for the configuration system."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from workflow_orchestrator.config.config_manager import (
    ConfigurationManager,
    AppConfig,
    create_config_manager,
)
from workflow_orchestrator.config.profile_loader import ProfileLoader
from workflow_orchestrator.config.validators import (
    validate_key,
    validate_profile_name,
    validate_url,
    ConfigValidationError,
)


class TestAppConfig:
    """Test suite for AppConfig."""

    def test_from_dict(self) -> None:
        """Test creating AppConfig from a dictionary."""
        config = AppConfig.from_dict({
            "brave_executable_path": "/usr/bin/brave",
            "vscode_executable_path": "/usr/bin/code",
            "unknown_key": "custom_value",
        })
        assert config.brave_executable_path == "/usr/bin/brave"
        assert config.vscode_executable_path == "/usr/bin/code"
        assert config.custom.get("unknown_key") == "custom_value"

    def test_to_dict(self) -> None:
        """Test serializing AppConfig to a dictionary."""
        config = AppConfig(
            brave_executable_path="/usr/bin/brave",
            default_project_directory="/home/user/project",
        )
        data = config.to_dict()
        assert data.get("brave_executable_path") == "/usr/bin/brave"
        assert data.get("default_project_directory") == "/home/user/project"
        assert "custom" not in data  # Only non-empty values included


class TestConfigurationManager:
    """Test suite for ConfigurationManager."""

    def setup_method(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / "data"
        self.config_dir.mkdir()
        self.config_file = self.config_dir / "config.json"
        self.profiles_dir = self.temp_dir / "profiles"
        self.profiles_dir.mkdir()

        # Create a basic config file
        config_data = {
            "brave_executable_path": "/usr/bin/brave",
            "default_project_directory": "/home/user/project",
        }
        self.config_file.write_text(json.dumps(config_data, indent=2))

        self.manager = ConfigurationManager(
            config_path=self.config_file,
            profiles_dir=self.profiles_dir,
        )

    def teardown_method(self) -> None:
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_base_config(self) -> None:
        """Test loading base configuration from JSON."""
        assert self.manager.config.brave_executable_path == "/usr/bin/brave"
        assert self.manager.config.default_project_directory == "/home/user/project"

    def test_set_and_get(self) -> None:
        """Test setting and getting configuration values."""
        self.manager.set("log_level", "DEBUG")
        assert self.manager.get("log_level") == "DEBUG"

    def test_get_default(self) -> None:
        """Test getting a default value for unset config."""
        assert self.manager.get("nonexistent", "default_val") == "default_val"

    def test_set_custom_key(self) -> None:
        """Test setting a custom (unknown) configuration key."""
        self.manager.set("my_custom_key", "custom_value")
        assert self.manager.get("my_custom_key") == "custom_value"

    def test_reload(self) -> None:
        """Test reloading configuration from all sources."""
        self.manager.reload()
        assert self.manager.config.brave_executable_path == "/usr/bin/brave"

    def test_profile_management(self) -> None:
        """Test listing and switching profiles."""
        # Create a test profile
        profile_file = self.profiles_dir / "test_profile.yaml"
        profile_file.write_text("default_project_directory: /home/test/project\n")

        profiles = self.manager.list_profiles()
        assert "test_profile" in profiles

        result = self.manager.switch_profile("test_profile")
        assert result
        assert self.manager.get_active_profile() == "test_profile"

    def test_switch_nonexistent_profile(self) -> None:
        """Test switching to a non-existent profile."""
        result = self.manager.switch_profile("nonexistent")
        assert not result

    def test_config_manager_singleton(self) -> None:
        """Test the module-level singleton."""
        from workflow_orchestrator.config.config_manager import get_config_manager
        mgr = get_config_manager()
        assert mgr is not None
        assert isinstance(mgr, ConfigurationManager)


class TestProfileLoader:
    """Test suite for ProfileLoader."""

    def setup_method(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.loader = ProfileLoader(self.temp_dir)

    def teardown_method(self) -> None:
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_default_profile(self) -> None:
        """Test loading the default profile (empty)."""
        data = self.loader.load("default")
        assert data == {}

    def test_load_custom_profile(self) -> None:
        """Test loading a custom profile."""
        profile_file = self.temp_dir / "home.yaml"
        profile_file.write_text("default_project_directory: /home/user\n")

        data = self.loader.load("home")
        assert data.get("default_project_directory") == "/home/user"

    def test_load_nonexistent_profile(self) -> None:
        """Test loading a non-existent profile."""
        data = self.loader.load("nonexistent")
        assert data == {}

    def test_list_profiles(self) -> None:
        """Test listing profiles."""
        assert self.loader.list_profiles() == ["default"]

        (self.temp_dir / "work.yaml").write_text("")
        (self.temp_dir / "home.yaml").write_text("")

        profiles = self.loader.list_profiles()
        assert "home" in profiles
        assert "work" in profiles

    def test_exists(self) -> None:
        """Test checking if a profile exists."""
        assert self.loader.exists("default")
        assert not self.loader.exists("nonexistent")

        (self.temp_dir / "custom.yaml").write_text("")
        assert self.loader.exists("custom")

    def test_clear_cache(self) -> None:
        """Test clearing the profile cache."""
        (self.temp_dir / "test.yaml").write_text("key: value")
        data1 = self.loader.load("test")
        assert data1.get("key") == "value"

        self.loader.clear_cache()

    def test_reload(self) -> None:
        """Test reloading a profile."""
        (self.temp_dir / "test.yaml").write_text("key: original")
        data = self.loader.reload("test")
        assert data.get("key") == "original"


class TestValidators:
    """Test suite for configuration validators."""

    def test_validate_key_known(self) -> None:
        """Test validating a known key with correct type."""
        validate_key("log_level", "INFO")  # Should not raise

    def test_validate_key_unknown(self) -> None:
        """Test that unknown keys raise."""
        with pytest.raises(ConfigValidationError, match="Unknown"):
            validate_key("nonexistent_key", "value")

    def test_validate_key_wrong_type(self) -> None:
        """Test that wrong types raise."""
        with pytest.raises(ConfigValidationError, match="Invalid type"):
            validate_key("log_to_file", "not_a_bool")

    def test_validate_key_invalid_log_level(self) -> None:
        """Test that invalid log levels raise."""
        with pytest.raises(ConfigValidationError, match="Invalid log level"):
            validate_key("log_level", "INVALID")

    def test_validate_profile_name_valid(self) -> None:
        assert validate_profile_name("home")
        assert validate_profile_name("work-v2")
        assert validate_profile_name("my_profile")

    def test_validate_profile_name_invalid(self) -> None:
        assert not validate_profile_name("")
        assert not validate_profile_name("  ")
        assert not validate_profile_name("with spaces")

    def test_validate_url(self) -> None:
        assert validate_url("")
        assert validate_url("https://example.com")
        assert validate_url("http://localhost:3000")
        assert not validate_url("ftp://invalid")
        assert not validate_url("not-a-url")
