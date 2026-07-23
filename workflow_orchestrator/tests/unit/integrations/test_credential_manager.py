"""Tests for CredentialManager integration module."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, Optional
from unittest.mock import MagicMock, patch

import pytest

from workflow_orchestrator.integrations.credential_manager import CredentialManager


@pytest.fixture
def temp_cred_dir() -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def manager(temp_cred_dir: Path) -> CredentialManager:
    return CredentialManager(storage_dir=temp_cred_dir)


class TestCredentialManager:
    """Tests for CredentialManager class."""

    def test_initial_state(self, manager: CredentialManager) -> None:
        assert manager.list_keys() == []

    def test_set_and_get(self, manager: CredentialManager) -> None:
        manager.set("test_key", "test-value-12345")
        value = manager.get("test_key")
        assert value == "test-value-12345"

    def test_set_api_key(self, manager: CredentialManager) -> None:
        manager.set_api_key("ANTHROPIC_API_KEY", "sk-ant-xxx")
        key = manager.get_api_key("ANTHROPIC_API_KEY")
        assert key == "sk-ant-xxx"

    def test_get_api_key_from_env(self, manager: CredentialManager) -> None:
        import os as _os
        with patch.dict(_os.environ, {"TEST_API_KEY": "env-value"}, clear=True):
            value = manager.get_api_key("TEST_API_KEY")
            assert value == "env-value"

    def test_get_nonexistent(self, manager: CredentialManager) -> None:
        value = manager.get("nonexistent")
        assert value is None

    def test_delete(self, manager: CredentialManager) -> None:
        manager.set("test_key", "test-value")
        result = manager.delete("test_key")
        assert result is True
        assert manager.get("test_key") is None

    def test_delete_nonexistent(self, manager: CredentialManager) -> None:
        result = manager.delete("nonexistent")
        assert result is False

    def test_list_keys(self, manager: CredentialManager) -> None:
        manager.set("key1", "value1")
        manager.set("key2", "value2")
        keys = manager.list_keys()
        assert "key1" in keys
        assert "key2" in keys

    def test_clear(self, manager: CredentialManager) -> None:
        manager.set("key1", "value1")
        manager.set("key2", "value2")
        manager.clear()
        assert manager.list_keys() == []

    def test_has_api_key(self, manager: CredentialManager) -> None:
        manager.set_api_key("ANTHROPIC_API_KEY", "sk-ant-xxx")
        assert manager.has_api_key("ANTHROPIC_API_KEY") is True

    def test_has_api_key_false(self, manager: CredentialManager) -> None:
        assert manager.has_api_key("NONEXISTENT") is False

    def test_persistence(self, temp_cred_dir: Path) -> None:
        m1 = CredentialManager(storage_dir=temp_cred_dir)
        m1.set("persistent", "value")
        m2 = CredentialManager(storage_dir=temp_cred_dir)
        assert m2.get("persistent") == "value"

    def test_empty_file(self, temp_cred_dir: Path) -> None:
        cred_file = temp_cred_dir / "credentials.json"
        cred_file.write_text("{}")
        manager = CredentialManager(storage_dir=temp_cred_dir)
        assert manager.list_keys() == []

    def test_corrupted_file(self, temp_cred_dir: Path) -> None:
        cred_file = temp_cred_dir / "credentials.json"
        cred_file.write_text("invalid json")
        manager = CredentialManager(storage_dir=temp_cred_dir)
        assert manager.list_keys() == []

    def test_oauth_tokens(self, manager: CredentialManager) -> None:
        manager.set_oauth_token("github", "gh_token", "refresh_token_val")
        tokens = manager.get_oauth_token("github")
        assert tokens is not None
        assert tokens["access_token"] == "gh_token"
        assert tokens["refresh_token"] == "refresh_token_val"

    def test_validate_api_key_format_valid(self, manager: CredentialManager) -> None:
        assert manager.validate_api_key_format("ANTHROPIC_API_KEY", "sk-ant-xxx123") is True

    def test_validate_api_key_format_invalid(self, manager: CredentialManager) -> None:
        assert manager.validate_api_key_format("ANTHROPIC_API_KEY", "short") is False

    def test_update_existing(self, manager: CredentialManager) -> None:
        manager.set("key", "original")
        manager.set("key", "updated")
        assert manager.get("key") == "updated"
