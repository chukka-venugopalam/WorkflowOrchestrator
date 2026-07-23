"""Graceful shutdown handler for the Workflow Orchestrator.

Manages clean teardown of services, resources, and state
during application shutdown.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from workflow_orchestrator.core.kernel import Kernel

logger = logging.getLogger(__name__)


class ShutdownHandler:
    """Handles graceful shutdown of the kernel and its services.

    Usage:
        >>> handler = ShutdownHandler(kernel)
        >>> handler.graceful_shutdown()
    """

    def __init__(self, kernel: Kernel) -> None:
        """Initialize the shutdown handler.

        Args:
            kernel: The kernel instance to manage shutdown for.
        """
        self._kernel = kernel
        self._shutdown_tasks: list[dict[str, Any]] = []

    def add_task(
        self,
        name: str,
        handler: Any,
        priority: int = 100,
        description: str = "",
    ) -> None:
        """Register a custom shutdown task.

        Args:
            name: Task name.
            handler: Callable to execute during shutdown.
            priority: Lower numbers run first.
            description: Human-readable description.
        """
        self._shutdown_tasks.append({
            "name": name,
            "handler": handler,
            "priority": priority,
            "description": description,
        })
        self._shutdown_tasks.sort(key=lambda t: t["priority"])

    def graceful_shutdown(self, exit_code: int = 0) -> None:
        """Execute graceful shutdown sequence.

        Args:
            exit_code: System exit code.
        """
        logger.info("Starting graceful shutdown...")

        # 1. Run custom shutdown tasks (in priority order)
        for task in self._shutdown_tasks:
            try:
                result = task["handler"]()
                logger.debug("Shutdown task '%s' completed: %s", task["name"], result)
            except Exception:
                logger.exception("Shutdown task '%s' failed", task["name"])

        # 2. Run kernel shutdown
        self._kernel.shutdown(exit_code)

        logger.info("Graceful shutdown complete")
