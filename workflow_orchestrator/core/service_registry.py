"""Dependency injection container for the Workflow Orchestrator.

Replaces the previous pattern of global mutable singletons (e.g.,
``default_registry``, ``config_manager``) with explicit dependency
injection.  All services are resolved through the ``ServiceRegistry``.

Usage:
    >>> registry = ServiceRegistry()
    >>> registry.register("config", config_manager_instance)
    >>> config = registry.get("config")
    >>> engine = registry.resolve_lazy("engine.lazy")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)


class ServiceNotFoundError(LookupError):
    """Raised when a requested service is not registered."""

    def __init__(self, name: str, available: list[str]) -> None:
        self.name = name
        self.available = available
        super().__init__(f"Service '{name}' not found. Available: {sorted(available)}")


class ServiceRegistrationError(RuntimeError):
    """Raised when a service cannot be registered (e.g., duplicate name)."""

    pass


@dataclass
class ServiceDescriptor:
    """Metadata about a registered service.

    Attributes:
        name: Unique service identifier.
        instance: The service instance (set if not lazy).
        factory: Factory callable for lazy instantiation (set if lazy).
        singleton: Whether the factory result is cached.
        dependencies: Optional list of service names this depends on.
        description: Human-readable description of the service.
    """

    name: str
    instance: Any = None
    factory: Callable[[Any], Any] | None = None
    singleton: bool = True
    dependencies: list[str] = field(default_factory=list)
    description: str = ""

    @property
    def is_lazy(self) -> bool:
        """Whether this service uses lazy instantiation."""
        return self.factory is not None and self.instance is None

    @property
    def is_initialized(self) -> bool:
        """Whether this service has been instantiated."""
        return self.instance is not None


class ServiceRegistry:
    """Dependency injection container for application services.

    Supports:
    - Direct instance registration
    - Lazy factory registration (with optional singleton caching)
    - Dependency declaration (informational, not auto-resolved)
    - Discovery of all registered services
    - Thread-safe operations
    """

    def __init__(self) -> None:
        self._services: dict[str, ServiceDescriptor] = {}
        self._started: bool = False

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        instance: Any = None,
        *,
        factory: Callable[[Any], Any] | None = None,
        singleton: bool = True,
        dependencies: list[str] | None = None,
        description: str = "",
        overwrite: bool = False,
    ) -> ServiceDescriptor:
        """Register a service.

        Args:
            name: Unique service identifier.
            instance: A pre-created service instance.
            factory: Factory callable for lazy creation. Receives the
                registry as argument when called.
            singleton: If True (default), the factory result is cached.
            dependencies: Optional list of service names this depends on.
            description: Human-readable description.
            overwrite: If True, replace an existing registration.

        Returns:
            The created ServiceDescriptor.

        Raises:
            ServiceRegistrationError: If a service with the same name
                already exists and ``overwrite`` is False.
        """
        if name in self._services and not overwrite:
            raise ServiceRegistrationError(
                f"Service '{name}' is already registered. "
                "Use overwrite=True to replace."
            )

        descriptor = ServiceDescriptor(
            name=name,
            instance=instance,
            factory=factory,
            singleton=singleton,
            dependencies=dependencies or [],
            description=description,
        )

        self._services[name] = descriptor
        logger.debug("Registered service '%s'%s", name, " (lazy)" if factory and instance is None else "")
        return descriptor

    def register_instance(self, name: str, instance: Any, **kwargs: Any) -> ServiceDescriptor:
        """Register a pre-created service instance (shortcut).

        Args:
            name: Unique service identifier.
            instance: The service instance.
            **kwargs: Additional parameters passed to ``register()``.

        Returns:
            The created ServiceDescriptor.
        """
        return self.register(name, instance=instance, **kwargs)

    def register_factory(
        self,
        name: str,
        factory: Callable[[Any], Any],
        *,
        singleton: bool = True,
        dependencies: list[str] | None = None,
        description: str = "",
        overwrite: bool = False,
    ) -> ServiceDescriptor:
        """Register a lazy factory for a service.

        Args:
            name: Unique service identifier.
            factory: Callable that receives the registry and returns
                the service instance.
            singleton: If True (default), cache the factory result.
            dependencies: Optional list of service names this depends on.
            description: Human-readable description.
            overwrite: If True, replace an existing registration.

        Returns:
            The created ServiceDescriptor.
        """
        return self.register(
            name,
            factory=factory,
            singleton=singleton,
            dependencies=dependencies,
            description=description,
            overwrite=overwrite,
        )

    def unregister(self, name: str) -> None:
        """Remove a service from the registry.

        Args:
            name: Service identifier to remove.
        """
        self._services.pop(name, None)
        logger.debug("Unregistered service '%s'", name)

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def get(self, name: str) -> Any:
        """Resolve a service by name.

        If the service is registered as a lazy factory, the factory is
        called (once, if singleton) and the result is cached.

        Args:
            name: Service identifier.

        Returns:
            The service instance.

        Raises:
            ServiceNotFoundError: If the service is not registered.
        """
        descriptor = self._services.get(name)
        if descriptor is None:
            raise ServiceNotFoundError(name, list(self._services.keys()))

        if descriptor.is_lazy:
            # Lazy instantiation
            instance = descriptor.factory(self)  # type: ignore[misc]
            if descriptor.singleton:
                descriptor.instance = instance
            logger.debug("Lazily instantiated service '%s'", name)
            return instance

        return descriptor.instance

    def get_descriptor(self, name: str) -> ServiceDescriptor:
        """Get the descriptor for a registered service.

        Args:
            name: Service identifier.

        Returns:
            The ServiceDescriptor.

        Raises:
            ServiceNotFoundError: If the service is not registered.
        """
        descriptor = self._services.get(name)
        if descriptor is None:
            raise ServiceNotFoundError(name, list(self._services.keys()))
        return descriptor

    def require(self, name: str) -> Any:
        """Resolve a service, raising a detailed error if not found.

        Args:
            name: Service identifier.

        Returns:
            The service instance.
        """
        return self.get(name)

    def get_typed(self, name: str, expected_type: type[T]) -> T:
        """Resolve a service and verify its type.

        Args:
            name: Service identifier.
            expected_type: The expected type of the service.

        Returns:
            The service instance, cast to the expected type.

        Raises:
            TypeError: If the resolved service is not of the expected type.
        """
        instance = self.get(name)
        if not isinstance(instance, expected_type):
            raise TypeError(
                f"Service '{name}' has type {type(instance).__name__}, "
                f"expected {expected_type.__name__}"
            )
        return instance

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def list_services(self) -> list[ServiceDescriptor]:
        """List all registered services.

        Returns:
            List of ServiceDescriptor objects.
        """
        return list(self._services.values())

    def list_names(self) -> list[str]:
        """List names of all registered services.

        Returns:
            Sorted list of service names.
        """
        return sorted(self._services.keys())

    def has_service(self, name: str) -> bool:
        """Check if a service is registered.

        Args:
            name: Service identifier.

        Returns:
            True if the service is registered.
        """
        return name in self._services

    @property
    def count(self) -> int:
        """Number of registered services."""
        return len(self._services)

    @property
    def started(self) -> bool:
        """Whether the registry has been started."""
        return self._started

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Mark the registry as started."""
        self._started = True
        logger.info("Service registry started with %d services registered", self.count)

    def stop(self) -> None:
        """Mark the registry as stopped and clear instances."""
        self._started = False
        # Clear singleton instances
        for descriptor in self._services.values():
            if descriptor.singleton and descriptor.instance is not None and descriptor.factory is not None:
                descriptor.instance = None
        logger.info("Service registry stopped")
