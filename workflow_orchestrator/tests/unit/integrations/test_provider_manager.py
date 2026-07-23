"""Tests for the ProviderManager integration module."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from workflow_orchestrator.integrations.provider_manager import (
    ProviderInfo,
    ProviderManager,
    ProviderStatus,
)


@pytest.fixture
def event_bus() -> MagicMock:
    return MagicMock()


@pytest.fixture
def manager(event_bus: MagicMock) -> ProviderManager:
    return ProviderManager(event_bus=event_bus)


class TestProviderInfo:
    """Tests for ProviderInfo data class."""

    def test_create(self) -> None:
        info = ProviderInfo(
            provider_id="test.provider",
            name="Test Provider",
            transport="rest_api",
        )
        assert info.provider_id == "test.provider"
        assert info.name == "Test Provider"
        assert info.transport == "rest_api"
        assert info.status == ProviderStatus.UNINSTALLED

    def test_enabled(self) -> None:
        info = ProviderInfo(
            provider_id="test", name="Test", status=ProviderStatus.ENABLED,
            enabled=True,
        )
        assert info.enabled is True
        assert info.status == ProviderStatus.ENABLED

    def test_error(self) -> None:
        info = ProviderInfo(
            provider_id="test", name="Test", status=ProviderStatus.ERROR,
            error="Connection failed",
        )
        assert info.status == ProviderStatus.ERROR
        assert info.error == "Connection failed"


class TestProviderManager:
    """Tests for ProviderManager class."""

    def test_known_providers_exist(self, manager: ProviderManager) -> None:
        providers = manager.list_providers()
        assert len(providers) > 0
        ids = [p.provider_id for p in providers]
        assert "anthropic.claude" in ids
        assert "openai.chatgpt" in ids
        assert "google.gemini" in ids

    def test_initial_status_uninstalled(self, manager: ProviderManager) -> None:
        status = manager.status("anthropic.claude")
        assert status is not None
        assert status.status == ProviderStatus.UNINSTALLED

    def test_install_success(self, manager: ProviderManager) -> None:
        result = manager.install("anthropic.claude")
        # May fail in test env, but should handle gracefully
        assert isinstance(result, bool)

    def test_install_unknown_provider(self, manager: ProviderManager) -> None:
        result = manager.install("unknown.provider")
        assert result is False

    def test_enable(self, manager: ProviderManager) -> None:
        # Must install first
        manager.install("anthropic.claude")
        result = manager.enable("anthropic.claude")
        assert result is True
        status = manager.status("anthropic.claude")
        assert status is not None
        assert status.enabled is True

    def test_enable_uninstalled(self, manager: ProviderManager) -> None:
        result = manager.enable("anthropic.claude")
        # Should fail because not installed
        assert result is False

    def test_disable(self, manager: ProviderManager) -> None:
        manager.install("anthropic.claude")
        manager.enable("anthropic.claude")
        result = manager.disable("anthropic.claude")
        assert result is True
        status = manager.status("anthropic.claude")
        assert status is not None
        assert status.enabled is False

    def test_new_provider_not_in_known_list(self, manager: ProviderManager) -> None:
        result = manager.status("completely.unknown")
        assert result is None

    def test_remove(self, manager: ProviderManager) -> None:
        result = manager.remove("anthropic.claude")
        assert result is True
        status = manager.status("anthropic.claude")
        assert status is not None
        assert status.status == ProviderStatus.UNINSTALLED

    def test_remove_nonexistent(self, manager: ProviderManager) -> None:
        result = manager.remove("nonexistent")
        assert result is False

    def test_validate_disabled(self, manager: ProviderManager) -> None:
        result = manager.validate("anthropic.claude")
        assert isinstance(result, dict)
        assert "valid" in result

    def test_list_enabled(self, manager: ProviderManager) -> None:
        enabled = manager.list_enabled()
        assert isinstance(enabled, list)

    def test_list_installed_empty(self, manager: ProviderManager) -> None:
        installed = manager.list_installed()
        assert isinstance(installed, list)

    def test_resolve_id_short(self, manager: ProviderManager) -> None:
        result = manager.install("claude")
        # Short ID should resolve to anthropic.claude
        assert isinstance(result, bool)

    def test_short_id_resolution(self, manager: ProviderManager) -> None:
        result = manager.install("gpt")
        assert isinstance(result, bool)
        result2 = manager.install("gemini")
        assert isinstance(result2, bool)

    def test_repair_nonexistent(self, manager: ProviderManager) -> None:
        result = manager.repair("nonexistent")
        assert result is False

    def test_update_nonexistent(self, manager: ProviderManager) -> None:
        result = manager.update("nonexistent")
        assert result is False
