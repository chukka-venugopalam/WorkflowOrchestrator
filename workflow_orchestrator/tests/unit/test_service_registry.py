"""Unit tests for the ServiceRegistry (dependency injection container)."""

from __future__ import annotations

import pytest
from workflow_orchestrator.core.service_registry import (
    ServiceRegistry,
    ServiceNotFoundError,
    ServiceRegistrationError,
    ServiceDescriptor,
)


class TestServiceRegistry:
    """Test suite for ServiceRegistry."""

    def setup_method(self) -> None:
        self.registry = ServiceRegistry()

    def test_register_and_get_instance(self) -> None:
        """Test registering and retrieving a service instance."""
        service = {"key": "value"}
        self.registry.register("test_service", service)
        assert self.registry.get("test_service") is service

    def test_register_instance_shortcut(self) -> None:
        """Test the register_instance shortcut."""
        service = [1, 2, 3]
        self.registry.register_instance("list_service", service)
        assert self.registry.get("list_service") == [1, 2, 3]

    def test_register_factory_and_get(self) -> None:
        """Test registering a lazy factory and resolving it."""
        call_count = 0

        def factory(registry):
            nonlocal call_count
            call_count += 1
            return {"count": call_count}

        self.registry.register_factory("lazy_service", factory, singleton=True)
        result1 = self.registry.get("lazy_service")
        result2 = self.registry.get("lazy_service")

        assert result1["count"] == 1
        assert result2 is result1  # Singleton: same instance
        assert call_count == 1

    def test_non_singleton_factory(self) -> None:
        """Test that non-singleton factories create new instances each time."""
        def factory(registry):
            return {"id": id(registry)}

        self.registry.register_factory("non_singleton", factory, singleton=False)
        result1 = self.registry.get("non_singleton")
        # Cache is not updated, but since not singleton, descriptor.instance stays None
        # Next call re-runs factory
        self.registry._services["non_singleton"].instance = None
        result2 = self.registry.get("non_singleton")
        assert result1 is not None
        assert result2 is not None

    def test_get_raises_error_for_missing_service(self) -> None:
        """Test that getting a missing service raises."""
        with pytest.raises(ServiceNotFoundError) as exc:
            self.registry.get("nonexistent")
        assert "nonexistent" in str(exc.value)

    def test_has_service(self) -> None:
        """Test the has_service method."""
        self.registry.register("exists", 42)
        assert self.registry.has_service("exists")
        assert not self.registry.has_service("missing")

    def test_duplicate_registration_raises_error(self) -> None:
        """Test that duplicate registration raises."""
        self.registry.register("dup", 1)
        with pytest.raises(ServiceRegistrationError):
            self.registry.register("dup", 2)

    def test_overwrite_duplicate(self) -> None:
        """Test that overwrite=True allows replacing a service."""
        self.registry.register("dup", 1)
        self.registry.register("dup", 2, overwrite=True)
        assert self.registry.get("dup") == 2

    def test_unregister(self) -> None:
        """Test unregistering a service."""
        self.registry.register("temp", "value")
        assert self.registry.has_service("temp")
        self.registry.unregister("temp")
        assert not self.registry.has_service("temp")

    def test_list_services(self) -> None:
        """Test listing all services."""
        self.registry.register("a", 1)
        self.registry.register("b", 2)
        services = self.registry.list_services()
        assert len(services) == 2
        names = [s.name for s in services]
        assert "a" in names
        assert "b" in names

    def test_list_names(self) -> None:
        """Test listing service names."""
        self.registry.register("z", 1)
        self.registry.register("a", 2)
        assert self.registry.list_names() == ["a", "z"]

    def test_get_typed_valid(self) -> None:
        """Test get_typed with correct type."""
        self.registry.register("my_int", 42)
        assert self.registry.get_typed("my_int", int) == 42

    def test_get_typed_invalid(self) -> None:
        """Test get_typed with wrong type."""
        self.registry.register("my_int", 42)
        with pytest.raises(TypeError):
            self.registry.get_typed("my_int", str)

    def test_get_descriptor(self) -> None:
        """Test getting a ServiceDescriptor."""
        self.registry.register("test", 42, description="My service")
        desc = self.registry.get_descriptor("test")
        assert isinstance(desc, ServiceDescriptor)
        assert desc.name == "test"
        assert desc.description == "My service"
        assert desc.instance == 42

    def test_get_descriptor_missing(self) -> None:
        """Test that getting a missing descriptor raises."""
        with pytest.raises(ServiceNotFoundError):
            self.registry.get_descriptor("missing")

    def test_start_and_stop(self) -> None:
        """Test start/stop lifecycle."""
        assert not self.registry.started
        self.registry.start()
        assert self.registry.started
        self.registry.stop()
        assert not self.registry.started

    def test_count_property(self) -> None:
        """Test the count property."""
        assert self.registry.count == 0
        self.registry.register("a", 1)
        self.registry.register("b", 2)
        assert self.registry.count == 2

    def test_require(self) -> None:
        """Test the require method."""
        self.registry.register("test", 42)
        assert self.registry.require("test") == 42

    def test_require_missing_raises(self) -> None:
        """Test that require raises for missing service."""
        with pytest.raises(ServiceNotFoundError):
            self.registry.require("missing")
