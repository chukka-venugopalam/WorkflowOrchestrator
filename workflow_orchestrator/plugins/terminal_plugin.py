"""Plugin for executing terminal commands.

Wraps the existing ``modules/terminal.py`` module to run
arbitrary shell commands as workflow steps.
"""

from __future__ import annotations

import shlex
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


class TerminalPlugin(Plugin):
    """Execute terminal commands and capture output."""

    metadata = PluginMetadata(
        name="terminal",
        description="Execute a shell command and capture its stdout, stderr, and exit code.",
        version="2.0.0",
    )

    def execute(
        self,
        step_config: dict[str, Any],
        context: dict[str, Any],
    ) -> StepResult:
        """Execute a terminal command.

        Supported step_config keys:
            - ``command`` (required): The shell command to run.
            - ``cwd``: Working directory (overrides context working_dir).
            - ``timeout``: Command timeout in seconds (default: 60).
        """
        terminal = _get_terminal_module()
        command = step_config.get("command", "")
        step_name = step_config.get("_step_name", f"Run: {command[:50]}")

        if not command:
            return self._failure(step_name, "No command provided. Set 'command' in step config.")

        # Resolve working directory
        from pathlib import Path
        cwd_str = step_config.get("cwd") or context.get("working_dir") or ""
        cwd = Path(cwd_str).expanduser().resolve() if cwd_str else None

        timeout = step_config.get("timeout", 60)

        result = terminal.run_command(command, cwd=cwd, timeout=timeout)

        output = {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
            "command": command,
        }

        if result.success:
            return self._success(
                step_name,
                f"Command completed (exit code 0).",
                output=output,
            )
        else:
            return self._failure(
                step_name,
                f"Command failed (exit code {result.exit_code}): {result.stderr[:200]}",
                output=output,
            )

    def validate_config(self, step_config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if not step_config.get("command"):
            errors.append("'command' is required for terminal steps")
        return errors


# Auto-register on import
default_registry.register(TerminalPlugin())
