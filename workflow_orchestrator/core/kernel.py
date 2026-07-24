"""Application kernel — the entry point for the Workflow Orchestrator.

The Kernel orchestrates:
- Startup sequence (configuration loading, plugin loading, service registration)
- Dependency injection through ServiceRegistry
- Lifecycle hook management
- Plugin discovery and loading
- Graceful shutdown

No workflow logic belongs here.  The kernel is pure infrastructure.

Usage:
    >>> kernel = Kernel.create_default()
    >>> kernel.boot()
    >>> # ... application runs ...
    >>> kernel.shutdown()
"""

from __future__ import annotations

import logging
import signal
import sys
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.core.service_registry import ServiceRegistry
from workflow_orchestrator.core.lifecycle import LifecycleManager, HookPriority
from workflow_orchestrator.core.bootstrap import BootstrapSequence
from workflow_orchestrator.core.shutdown import ShutdownHandler

logger = logging.getLogger(__name__)


class Kernel:
    """Application kernel — orchestrates startup, dependency injection, and shutdown.

    The Kernel is the single entry point for the application. It manages
    the lifecycle of all services through the ServiceRegistry and
    LifecycleManager.
    """

    def __init__(
        self,
        registry: ServiceRegistry | None = None,
        lifecycle: LifecycleManager | None = None,
    ) -> None:
        """Initialize the kernel.

        Args:
            registry: Service registry for dependency injection.
                Creates a new one if not provided.
            lifecycle: Lifecycle manager for startup/shutdown hooks.
                Creates a new one if not provided.
        """
        self._registry = registry or ServiceRegistry()
        self._lifecycle = lifecycle or LifecycleManager()
        self._booted: bool = False
        self._shutdown_requested: bool = False
        self._bootstrap: BootstrapSequence = BootstrapSequence(self)
        self._shutdown_handler: ShutdownHandler = ShutdownHandler(self)

        # Register self
        self._registry.register_instance("kernel", self, description="Application kernel")

    @classmethod
    def create_default(cls) -> Kernel:
        """Create a kernel with default service registrations.

        Returns:
            A fully set up Kernel instance.
        """
        kernel = cls()
        bootstrap = kernel._bootstrap
        bootstrap.register_default_services()
        return kernel

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def registry(self) -> ServiceRegistry:
        """The service registry."""
        return self._registry

    @property
    def lifecycle(self) -> LifecycleManager:
        """The lifecycle manager."""
        return self._lifecycle

    @property
    def booted(self) -> bool:
        """Whether the kernel has been booted."""
        return self._booted

    @property
    def shutdown_requested(self) -> bool:
        """Whether shutdown has been requested."""
        return self._shutdown_requested

    @property
    def bootstrap(self) -> BootstrapSequence:
        """The bootstrap sequence."""
        return self._bootstrap

    @property
    def shutdown_handler(self) -> ShutdownHandler:
        """The shutdown handler."""
        return self._shutdown_handler

    # ------------------------------------------------------------------
    # Boot / Shutdown
    # ------------------------------------------------------------------

    def boot(
        self,
        register_defaults: bool = True,
        discover_plugins: bool = True,
        setup_signal_handlers: bool = True,
    ) -> bool:
        """Boot the kernel: run the full startup sequence.

        Args:
            register_defaults: Register default services.
            discover_plugins: Discover and load plugins.
            setup_signal_handlers: Register signal handlers for graceful shutdown.

        Returns:
            True if boot completed successfully.
        """
        if self._booted:
            logger.warning("Kernel is already booted")
            return True

        logger.info("Booting Workflow Orchestrator kernel...")

        # Register default framework services
        if register_defaults:
            self._bootstrap.register_default_services()

        # Run startup lifecycle hooks
        success = self._lifecycle.run_startup()

        # Register signal handlers for graceful shutdown
        if setup_signal_handlers:
            self._setup_signal_handlers()

        self._registry.start()

        if success:
            self._booted = True
            logger.info(
                "Kernel booted successfully (%d services, %d startup hooks)",
                self._registry.count,
                self._lifecycle.startup_count,
            )
        else:
            logger.error("Kernel boot completed with errors")

        return success

    def shutdown(self, exit_code: int = 0) -> None:
        """Gracefully shut down the kernel.

        Args:
            exit_code: System exit code to use.
        """
        if self._shutdown_requested:
            return

        self._shutdown_requested = True
        logger.info("Shutting down kernel...")

        # Run shutdown lifecycle hooks
        self._lifecycle.run_shutdown()

        # Stop the service registry
        self._registry.stop()

        self._booted = False
        logger.info("Kernel shut down complete")

    # ------------------------------------------------------------------
    # Plugin management
    # ------------------------------------------------------------------

    def discover_plugins(self, package: str = "workflow_orchestrator.plugins") -> int:
        """Discover and load plugins.

        Args:
            package: The Python package to scan for plugins.

        Returns:
            Number of plugins discovered.
        """
        from workflow_orchestrator.plugins.registry import PluginRegistry

        if not self._registry.has_service("plugin_registry"):
            logger.warning("No plugin_registry registered in kernel")
            return 0
        registry = self._registry.get_typed("plugin_registry", PluginRegistry)
        count = registry.discover(package)
        logger.info("Discovered %d plugins", count)
        return count

    # ------------------------------------------------------------------
    # Signal handling
    # ------------------------------------------------------------------

    def _setup_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""
        def _handle_signal(signum: int, frame: Any) -> None:
            """Handle OS signals for graceful shutdown."""
            signal_name = signal.Signals(signum).name
            logger.info("Received signal %s, initiating graceful shutdown...", signal_name)
            self.shutdown(exit_code=128 + signum)
            sys.exit(128 + signum)

        # Register for SIGINT (Ctrl+C) and SIGTERM
        if hasattr(signal, "SIGINT"):
            signal.signal(signal.SIGINT, _handle_signal)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _handle_signal)

    # ------------------------------------------------------------------
    # Service access shortcuts
    # ------------------------------------------------------------------

    def get_service(self, name: str) -> Any:
        """Get a service from the registry.

        Args:
            name: Service identifier.

        Returns:
            The service instance.
        """
        return self._registry.get(name)

    def register_service(self, name: str, instance: Any, **kwargs: Any) -> None:
        """Register a service.

        Args:
            name: Service identifier.
            instance: The service instance.
            **kwargs: Additional parameters.
        """
        self._registry.register_instance(name, instance, **kwargs)
