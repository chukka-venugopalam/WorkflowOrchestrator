"""Tests for ProviderConfiguration integration module."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, Optional
from unittest.mock import MagicMock, patch

import pytest

from workflow_orchestrator.integrations.provider_configuration import ProviderConfiguration


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def config(temp_dir: Path) -> ProviderConfiguration:
    return ProviderConfiguration(config_dir=temp_dir)


class TestProviderConfiguration:
    """Tests for ProviderConfiguration class."""

    def test_get_default(self, temp_dir: Path) -> None:
        config = ProviderConfiguration(config_dir=temp_dir)
        default = config.get_default("claude")
        assert default is not None
        assert default["provider_id"] == "anthropic.claude"
        assert default["transport"] == "rest_api"

    def test_get_default_chatgpt(self, temp_dir: Path) -> None:
        config = ProviderConfiguration(config_dir=temp_dir)
        default = config.get_default("chatgpt")
        assert default is not None
        assert default["provider_id"] == "openai.chatgpt"

    def test_get_default_unknown(self, temp_dir: Path) -> None:
        config = ProviderConfiguration(config_dir=temp_dir)
        assert config.get_default("nonexistent") is None

    def test_write_and_read(self, config: ProviderConfiguration) -> None:
        data = {"name": "Test", "provider_id": "test.provider", "transport": "cli"}
        path = config.write("test", data)
        assert path.exists()
        read_data = config.read("test")
        assert read_data is not None
        assert read_data["name"] == "Test"
        assert read_data["provider_id"] == "test.provider"

    def test_read_nonexistent(self, config: ProviderConfiguration) -> None:
        assert config.read("nonexistent") is None

    def test_create_default(self, config: ProviderConfiguration) -> None:
        result = config.create_default("claude")
        assert result is not None
        assert result["name"] == "Claude"
        assert config.read("claude") is not None

    def test_create_default_unknown(self, config: ProviderConfiguration) -> None:
        result = config.create_default("nonexistent")
        assert result is None

    def test_create_all_defaults(self, config: ProviderConfiguration) -> None:
        created = config.create_all_defaults()
        assert len(created) > 0
        assert "claude" in created

    def test_list_configs(self, config: ProviderConfiguration) -> None:
        config.create_default("claude")
        config.create_default("gemini")
        configs = config.list_configs()
        assert "claude" in configs
        assert "gemini" in configs

    def test_empty_list(self, temp_dir: Path) -> None:
        config = ProviderConfiguration(config_dir=temp_dir)
        assert config.list_configs() == []

    def test_validate_valid(self, config: ProviderConfiguration) -> None:
        cfg = {"name": "Test", "provider_id": "test.id", "transport": "rest_api"}
        result = config.validate(cfg)
        assert result["valid"] is True

    def test_validate_missing_fields(self, config: ProviderConfiguration) -> None:
        cfg = {"name": "Test"}
        result = config.validate(cfg)
        assert result["valid"] is False
        assert len(result["issues"]) > 0

    def test_validate_invalid_transport(self, config: ProviderConfiguration) -> None:
        cfg = {"name": "Test", "provider_id": "test.id", "transport": "invalid"}
        result = config.validate(cfg)
        assert result["valid"] is False

    def test_to_json(self, config: ProviderConfiguration) -> None:
        cfg = {"name": "Test", "provider_id": "test.id"}
        json_str = config.to_json(cfg)
        assert isinstance(json_str, str)
        assert "Test" in json_str
