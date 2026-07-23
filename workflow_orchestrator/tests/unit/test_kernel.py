"""Unit tests for the Kernel (application entry point)."""

from __future__ import annotations

from workflow_orchestrator.core.kernel import Kernel
from workflow_orchestrator.core.service_registry import ServiceRegistry, ServiceNotFoundError
from workflow_orchestrator.core.lifecycle import LifecycleManager


class TestKernel:
    """Test suite for Kernel."""

    def setup_method(self) -> None:
        self.kernel = Kernel()

    def test_kernel_initial_state(self) -> None:
        """Test kernel initial state."""
        assert not self.kernel.booted
        assert not self.kernel.shutdown_requested
        assert self.kernel.registry is not None
        assert self.kernel.lifecycle is not None

    def test_kernel_create_default(self) -> None:
        """Test creating a kernel with default services."""
        kernel = Kernel.create_default()
        assert kernel.registry.count > 0
        assert kernel.lifecycle.startup_count > 0

    def test_boot(self) -> None:
        """Test booting the kernel."""
        result = self.kernel.boot(register_defaults=False, discover_plugins=False, setup_signal_handlers=False)
        assert result
        assert self.kernel.booted

    def test_double_boot(self) -> None:
        """Test that double boot is safe."""
        self.kernel.boot(register_defaults=False, discover_plugins=False, setup_signal_handlers=False)
        result = self.kernel.boot(register_defaults=False, discover_plugins=False, setup_signal_handlers=False)
        assert result  # Should succeed without error

    def test_shutdown(self) -> None:
        """Test kernel shutdown."""
        self.kernel.boot(register_defaults=False, discover_plugins=False, setup_signal_handlers=False)
        assert self.kernel.booted
        self.kernel.shutdown()
        assert not self.kernel.booted
        assert self.kernel.shutdown_requested

    def test_double_shutdown(self) -> None:
        """Test that double shutdown is safe."""
        self.kernel.shutdown()
        self.kernel.shutdown()  # Should not raise

    def test_get_service(self) -> None:
        """Test getting a service from the kernel."""
        self.kernel.registry.register_instance("test", 42)
        assert self.kernel.get_service("test") == 42

    def test_register_service(self) -> None:
        """Test registering a service through the kernel."""
        self.kernel.register_service("my_service", {"key": "value"})
        assert self.kernel.get_service("my_service") == {"key": "value"}

    def test_service_registry_injection(self) -> None:
        """Test injecting a custom registry."""
        custom_registry = ServiceRegistry()
        kernel = Kernel(registry=custom_registry)
        assert kernel.registry is custom_registry

    def test_lifecycle_injection(self) -> None:
        """Test injecting a custom lifecycle manager."""
        custom_lifecycle = LifecycleManager()
        kernel = Kernel(lifecycle=custom_lifecycle)
        assert kernel.lifecycle is custom_lifecycle

    def test_discover_plugins_no_registry(self) -> None:
        """Test plugin discovery with no plugin registry registered."""
        count = self.kernel.discover_plugins()
        assert count == 0  # No registry registered

    def test_kernel_self_registration(self) -> None:
        """Test that the kernel registers itself."""
        assert self.kernel.registry.has_service("kernel")
        assert self.kernel.registry.get("kernel") is self.kernel
