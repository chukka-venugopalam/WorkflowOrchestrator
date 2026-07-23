"""Tests for ApiManager integration module."""

from __future__ import annotations

from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from workflow_orchestrator.integrations.api_manager import ApiManager, ApiProviderInfo


class TestApiProviderInfo:
    """Tests for ApiProviderInfo data class."""

    def test_create(self) -> None:
        ep = ApiProviderInfo(
            name="test-api",
            base_url="https://api.example.com",
            auth_type="api_key",
        )
        assert ep.name == "test-api"
        assert ep.base_url == "https://api.example.com"
        assert ep.auth_type == "api_key"
        assert ep.health_status == "unknown"


class TestApiManager:
    """Tests for ApiManager class."""

    def test_initial_state(self) -> None:
        event_bus = MagicMock()
        manager = ApiManager(event_bus=event_bus)
        assert manager.list_providers() == []

    def test_register(self) -> None:
        event_bus = MagicMock()
        manager = ApiManager(event_bus=event_bus)
        info = manager.register("test", "https://test.com", "none")
        assert info.name == "test"
        assert manager.list_providers() != []

    def test_unregister(self) -> None:
        event_bus = MagicMock()
        manager = ApiManager(event_bus=event_bus)
        manager.register("test", "https://test.com", "none")
        result = manager.unregister("test")
        assert result is True
        assert manager.list_providers() == []

    def test_unregister_nonexistent(self) -> None:
        event_bus = MagicMock()
        manager = ApiManager(event_bus=event_bus)
        result = manager.unregister("nonexistent")
        assert result is False

    def test_get_provider(self) -> None:
        event_bus = MagicMock()
        manager = ApiManager(event_bus=event_bus)
        manager.register("my-api", "https://my.com", "api_key")
        retrieved = manager.get_provider("my-api")
        assert retrieved is not None
        assert retrieved.name == "my-api"

    def test_get_provider_nonexistent(self) -> None:
        event_bus = MagicMock()
        manager = ApiManager(event_bus=event_bus)
        retrieved = manager.get_provider("nonexistent")
        assert retrieved is None

    def test_list_providers(self) -> None:
        event_bus = MagicMock()
        manager = ApiManager(event_bus=event_bus)
        manager.register("e1", "https://e1.com", "none")
        manager.register("e2", "https://e2.com", "api_key")
        assert len(manager.list_providers()) == 2

    def test_check_health_unknown(self) -> None:
        event_bus = MagicMock()
        manager = ApiManager(event_bus=event_bus)
        health = manager.check_health("nonexistent")
        assert health.get("healthy") is False

    def test_check_all_health(self) -> None:
        event_bus = MagicMock()
        manager = ApiManager(event_bus=event_bus)
        manager.register("test", "https://test.com", "none")
        results = manager.check_all_health()
        assert "test" in results
