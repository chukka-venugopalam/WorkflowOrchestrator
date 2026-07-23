"""Tests for TransportFactory integration module."""

from __future__ import annotations

from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from workflow_orchestrator.integrations.transport_factory import TransportFactory


@pytest.fixture
def event_bus() -> MagicMock:
    return MagicMock()


@pytest.fixture
def factory(event_bus: MagicMock) -> TransportFactory:
    return TransportFactory(event_bus=event_bus)


class TestTransportFactory:
    """Tests for TransportFactory class."""

    def test_list_types(self, factory: TransportFactory) -> None:
        types = factory.list_types()
        assert "rest_api" in types
        assert "cli" in types
        assert "browser" in types
        assert "desktop" in types
        assert "mcp" in types
        assert "ssh" in types

    def test_create_rest_api(self, factory: TransportFactory) -> None:
        transport = factory.create("rest_api")
        assert transport is not None

    def test_create_cli(self, factory: TransportFactory) -> None:
        transport = factory.create("cli")
        assert transport is not None

    def test_create_browser(self, factory: TransportFactory) -> None:
        transport = factory.create("browser", {"headless": True})
        assert transport is not None

    def test_create_desktop(self, factory: TransportFactory) -> None:
        transport = factory.create("desktop")
        assert transport is not None

    def test_create_mcp(self, factory: TransportFactory) -> None:
        transport = factory.create("mcp")
        assert transport is not None

    def test_create_ssh(self, factory: TransportFactory) -> None:
        transport = factory.create("ssh")
        assert transport is not None

    def test_create_unknown_type(self, factory: TransportFactory) -> None:
        transport = factory.create("nonexistent")
        assert transport is None

    def test_create_all(self, factory: TransportFactory) -> None:
        configs = {
            "rest_api": {},
            "cli": {},
        }
        results = factory.create_all(configs)
        assert "rest_api" in results
        assert "cli" in results

    def test_register_type(self, factory: TransportFactory) -> None:
        factory.register_type("custom", "workflow_orchestrator.transports.transport", "BaseTransport")
        types = factory.list_types()
        assert "custom" in types

    def test_clear_cache(self, factory: TransportFactory) -> None:
        factory.create("rest_api")
        factory.clear_cache()
        # Should not raise
        assert True
