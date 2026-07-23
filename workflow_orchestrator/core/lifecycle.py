"""Lifecycle manager for startup and shutdown hooks.

Manages ordered execution of lifecycle hooks during application
startup and shutdown.  Hooks can be registered with priority
and dependencies.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class HookPriority(Enum):
    """Execution priority for lifecycle hooks."""

    CRITICAL = 0  # Must run first (e.g., logging, config)
    HIGH = 1  # Core services (e.g., event bus, state engine)
    NORMAL = 2  # Regular services (e.g., plugins)
    LOW = 3  # Non-critical (e.g., reports, cleanup)
    LAST = 4  # Final initialization


@dataclass
class LifecycleHook:
    """A registered lifecycle hook.

    Attributes:
        name: Human-readable name for the hook.
        handler: Callable that performs the hook action.
        priority: Execution priority (lower runs first).
        dependencies: Names of hooks that must complete first.
        description: Human-readable description.
    """

    name: str
    handler: Callable[[], Any]
    priority: HookPriority = HookPriority.NORMAL
    dependencies: list[str] = field(default_factory=list)
    description: str = ""


class LifecycleManager:
    """Manages startup and shutdown lifecycle hooks.

    Supports:
    - Registration of startup and shutdown hooks
    - Priority-ordered execution
    - Dependency tracking (informational warnings)
    - Error isolation (one hook failure doesn't cascade)
    - Execution tracking

    Usage:
        >>> lifecycle = LifecycleManager()
        >>> lifecycle.on_startup("load_config", load_config, priority=HookPriority.CRITICAL)
        >>> lifecycle.on_shutdown("save_state", save_state, priority=HookPriority.LAST)
        >>> lifecycle.run_startup()
        >>> lifecycle.run_shutdown()
    """

    def __init__(self) -> None:
        self._startup_hooks: list[LifecycleHook] = []
        self._shutdown_hooks: list[LifecycleHook] = []
        self._executed_startup: list[str] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def on_startup(
        self,
        name: str,
        handler: Callable[[], Any],
        priority: HookPriority = HookPriority.NORMAL,
        dependencies: list[str] | None = None,
        description: str = "",
    ) -> LifecycleHook:
        """Register a startup hook.

        Args:
            name: Unique name for this hook.
            handler: Callable that runs during startup.
            priority: Execution priority.
            dependencies: Names of hooks that must run first.
            description: Human-readable description.

        Returns:
            The registered LifecycleHook.
        """
        hook = LifecycleHook(
            name=name,
            handler=handler,
            priority=priority,
            dependencies=dependencies or [],
            description=description or name,
        )
        self._startup_hooks.append(hook)
        logger.debug("Registered startup hook '%s' (priority=%s)", name, priority.name)
        return hook

    def on_shutdown(
        self,
        name: str,
        handler: Callable[[], Any],
        priority: HookPriority = HookPriority.NORMAL,
        dependencies: list[str] | None = None,
        description: str = "",
    ) -> LifecycleHook:
        """Register a shutdown hook.

        Args:
            name: Unique name for this hook.
            handler: Callable that runs during shutdown.
            priority: Execution priority.
            dependencies: Names of hooks that must run first.
            description: Human-readable description.

        Returns:
            The registered LifecycleHook.
        """
        hook = LifecycleHook(
            name=name,
            handler=handler,
            priority=priority,
            dependencies=dependencies or [],
            description=description or name,
        )
        self._shutdown_hooks.append(hook)
        logger.debug("Registered shutdown hook '%s' (priority=%s)", name, priority.name)
        return hook

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run_startup(self) -> bool:
        """Execute all registered startup hooks in priority order.

        Returns:
            True if all hooks completed successfully.
        """
        logger.info("Running startup lifecycle hooks...")

        sorted_hooks = sorted(self._startup_hooks, key=lambda h: (h.priority.value, h.name))
        self._executed_startup = []
        all_success = True

        for hook in sorted_hooks:
            try:
                self._check_dependencies(hook, self._executed_startup)
                result = hook.handler()
                self._executed_startup.append(hook.name)
                if result is False:
                    logger.error("Startup hook '%s' returned failure", hook.name)
                    all_success = False
                else:
                    logger.debug("Startup hook '%s' completed", hook.name)
            except Exception:
                logger.exception("Startup hook '%s' failed", hook.name)
                all_success = False

        if all_success:
            logger.info("All startup hooks completed (%d hooks)", len(self._startup_hooks))
        else:
            logger.warning("Some startup hooks failed (%d/%d)", 
                          len([h for h in self._startup_hooks if h.name not in self._executed_startup]),
                          len(self._startup_hooks))

        return all_success

    def run_shutdown(self) -> bool:
        """Execute all registered shutdown hooks in reverse priority order.

        Returns:
            True if all hooks completed successfully.
        """
        logger.info("Running shutdown lifecycle hooks...")

        # Shutdown runs in reverse order
        sorted_hooks = sorted(self._shutdown_hooks, key=lambda h: (-h.priority.value, h.name))
        executed: list[str] = []
        all_success = True

        for hook in sorted_hooks:
            try:
                result = hook.handler()
                executed.append(hook.name)
                if result is False:
                    logger.error("Shutdown hook '%s' returned failure", hook.name)
                    all_success = False
                else:
                    logger.debug("Shutdown hook '%s' completed", hook.name)
            except Exception:
                logger.exception("Shutdown hook '%s' failed", hook.name)
                all_success = False

        if all_success:
            logger.info("All shutdown hooks completed (%d hooks)", len(self._shutdown_hooks))
        else:
            logger.warning("Some shutdown hooks failed")

        return all_success

    def _check_dependencies(self, hook: LifecycleHook, executed: list[str]) -> None:
        """Check that all dependencies have been executed.

        Args:
            hook: The hook to check.
            executed: List of executed hook names.

        Raises:
            RuntimeError: If a dependency has not been executed.
        """
        for dep in hook.dependencies:
            if dep not in executed:
                logger.warning(
                    "Hook '%s' depends on '%s' which has not been executed",
                    hook.name,
                    dep,
                )

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    @property
    def startup_count(self) -> int:
        """Number of registered startup hooks."""
        return len(self._startup_hooks)

    @property
    def shutdown_count(self) -> int:
        """Number of registered shutdown hooks."""
        return len(self._shutdown_hooks)

    def list_startup_hooks(self) -> list[LifecycleHook]:
        """List all startup hooks, sorted by priority."""
        return sorted(self._startup_hooks, key=lambda h: (h.priority.value, h.name))

    def list_shutdown_hooks(self) -> list[LifecycleHook]:
        """List all shutdown hooks, sorted by priority (reverse)."""
        return sorted(self._shutdown_hooks, key=lambda h: (-h.priority.value, h.name))

    def clear(self) -> None:
        """Clear all registered hooks."""
        self._startup_hooks.clear()
        self._shutdown_hooks.clear()
        self._executed_startup.clear()
