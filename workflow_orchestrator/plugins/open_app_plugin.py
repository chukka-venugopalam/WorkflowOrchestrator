"""Plugin for launching arbitrary desktop applications.

Provides a generic way to open any application by name or path.
Wraps the ``modules/terminal`` module for launching processes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow_orchestrator.models import StepResult, StepStatus
from workflow_orchestrator.plugins.base import Plugin, PluginMetadata
from workflow_orchestrator.plugins.registry import default_registry

_terminal_module = None


def _get_terminal_module():
    global _terminal_module
    if _terminal_module is None:
        from workflow_orchestrator.modules import terminal as _terminal_module
    return _terminal_module


_utils_module = None


def _get_utils_module():
    global _utils_module
    if _utils_module is None:
        from workflow_orchestrator.modules import utils as _utils_module
    return _utils_module


class OpenAppPlugin(Plugin):
    """Open a desktop application by name or path."""

    metadata = PluginMetadata(
        name="open_app",
        description="Open a desktop application (VS Code, browser, terminal, etc.) by name or executable path.",
        version="2.0.0",
    )

    def execute(
        self,
        step_config: dict[str, Any],
        context: dict[str, Any],
    ) -> StepResult:
        """Open an application.

        Supported step_config keys:
            - ``app`` (required): Application name or executable path.
            - ``args``: Additional command-line arguments (list or string).
            - ``wait``: Whether to wait for the app to close (default: False).
        """
        terminal = _get_terminal_module()
        utils = _get_utils_module()
        app = step_config.get("app", "")
        step_name = step_config.get("_step_name", f"Open {app}")

        if not app:
            return self._failure(step_name, "No application specified. Set 'app' in step config.")

        # Try to find the executable
        resolved = utils.find_executable(app)
        if not resolved:
            # If not found in PATH, try using it as a direct path
            resolved = app

        # Build command
        args = step_config.get("args", "")
        if isinstance(args, list):
            args_str = " ".join(str(a) for a in args)
        else:
            args_str = str(args) if args else ""

        command = f'"{resolved}" {args_str}'.strip()

        wait = step_config.get("wait", False)

        try:
            if wait:
                result = terminal.run_command(command, timeout=step_config.get("timeout", 120))
                output = {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.exit_code,
                    "app": app,
                }
                if result.success:
                    return self._success(step_name, f"Application '{app}' exited successfully.", output=output)
                return self._failure(
                    step_name,
                    f"Application '{app}' failed (exit code {result.exit_code}).",
                    output=output,
                )
            else:
                terminal.run_command_async(command)
                return self._success(step_name, f"Application '{app}' launched.", output={"app": app, "command": command})
        except Exception as exc:
            return self._failure(step_name, f"Failed to launch '{app}': {exc}")

    def validate_config(self, step_config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if not step_config.get("app"):
            errors.append("'app' is required (application name or executable path)")
        return errors


# Auto-register on import
default_registry.register(OpenAppPlugin())
