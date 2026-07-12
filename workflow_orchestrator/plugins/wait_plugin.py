"""Plugin for introducing delays between workflow steps.

This is a pure time-based plugin that does not wrap any
existing module - it simply sleeps for a configured duration.
"""

from __future__ import annotations

import time
from typing import Any

from workflow_orchestrator.models import StepResult, StepStatus
from workflow_orchestrator.plugins.base import Plugin, PluginMetadata
from workflow_orchestrator.plugins.registry import default_registry


class WaitPlugin(Plugin):
    """Pause workflow execution for a specified duration."""

    metadata = PluginMetadata(
        name="wait",
        description="Pause workflow execution for a specified number of seconds.",
        version="2.0.0",
    )

    def execute(
        self,
        step_config: dict[str, Any],
        context: dict[str, Any],
    ) -> StepResult:
        """Wait for a specified duration.

        Supported step_config keys:
            - ``seconds`` (required): Number of seconds to wait.
            - ``message``: Optional message to display during the wait.
        """
        seconds = step_config.get("seconds", 0)
        step_name = step_config.get("_step_name", f"Wait {seconds}s")

        if seconds <= 0:
            return self._success(step_name, "No wait time specified (0 seconds).")

        message = step_config.get("message", f"Waiting for {seconds} seconds...")

        # Log the wait, then sleep
        time.sleep(seconds)

        return self._success(
            step_name,
            f"Waited for {seconds} seconds.",
            output={"seconds": seconds, "message": message},
        )

    def validate_config(self, step_config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        seconds = step_config.get("seconds", 0)
        if not isinstance(seconds, (int, float)) or seconds < 0:
            errors.append("'seconds' must be a non-negative number")
        return errors


# Auto-register on import
default_registry.register(WaitPlugin())
