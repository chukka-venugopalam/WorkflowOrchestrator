"""Plugin base classes and interfaces.

All workflow plugins must inherit from `Plugin` and implement
the `execute` method. Each plugin is a stateless executor for
a specific type of workflow step.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from workflow_orchestrator.models import StepResult, StepStatus


@dataclass
class PluginMetadata:
    """Metadata describing a plugin.

    Attributes:
        name: Unique plugin identifier (e.g., 'terminal', 'browser').
        description: Human-readable description of what the plugin does.
        version: Plugin version string.
        author: Plugin author (optional).
    """

    name: str
    description: str = ""
    version: str = "1.0.0"
    author: str = ""


class Plugin(ABC):
    """Abstract base class for all workflow plugins.

    Subclasses must provide a `metadata` class variable and
    implement the `execute` method.

    Plugins are stateless: all state is passed via the
    ``step_config`` and ``context`` parameters and returned
    via ``StepResult.output``.
    """

    metadata: PluginMetadata

    @abstractmethod
    def execute(
        self,
        step_config: dict[str, Any],
        context: dict[str, Any],
    ) -> StepResult:
        """Execute the plugin action.

        Args:
            step_config: Plugin-specific configuration from the workflow step.
            context: Shared execution context (e.g., accumulated outputs
                from previous steps, environment variables).

        Returns:
            StepResult: Outcome of the execution, including status,
                output data, and any error information.
        """
        ...

    def validate_config(self, step_config: dict[str, Any]) -> list[str]:
        """Validate the step configuration and return error messages.

        Override this method to provide custom validation. Base
        implementation returns an empty list (no errors).

        Args:
            step_config: Plugin-specific configuration dictionary.

        Returns:
            list[str]: List of validation error messages. An empty list
                means the configuration is valid.
        """
        _ = step_config
        return []

    @property
    def name(self) -> str:
        """Shortcut to ``self.metadata.name``."""
        return self.metadata.name

    @property
    def description(self) -> str:
        """Shortcut to ``self.metadata.description``."""
        return self.metadata.description

    def _success(
        self,
        step_name: str,
        message: str = "",
        output: dict[str, Any] | None = None,
    ) -> StepResult:
        """Create a successful StepResult."""
        return StepResult(
            step_name=step_name,
            plugin=self.name,
            status=StepStatus.SUCCESS,
            message=message or "Step completed successfully.",
            output=output or {},
        )

    def _failure(
        self,
        step_name: str,
        error: str,
        output: dict[str, Any] | None = None,
    ) -> StepResult:
        """Create a failed StepResult."""
        return StepResult(
            step_name=step_name,
            plugin=self.name,
            status=StepStatus.FAILURE,
            message=f"Step failed: {error}",
            output=output or {},
            error=error,
        )
