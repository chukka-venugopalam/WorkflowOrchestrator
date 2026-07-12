"""Plugin for opening VS Code with projects or files.

Wraps the existing ``modules/vscode.py`` module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow_orchestrator.models import StepResult, StepStatus
from workflow_orchestrator.plugins.base import Plugin, PluginMetadata
from workflow_orchestrator.plugins.registry import default_registry

_vscode_module = None


def _get_vscode_module():
    global _vscode_module
    if _vscode_module is None:
        from workflow_orchestrator.modules import vscode as _vscode_module
    return _vscode_module


class VSCodePlugin(Plugin):
    """Open VS Code with a project directory or file."""

    metadata = PluginMetadata(
        name="vscode",
        description="Open VS Code with a project directory or a specific file.",
        version="2.0.0",
    )

    def execute(
        self,
        step_config: dict[str, Any],
        context: dict[str, Any],
    ) -> StepResult:
        """Open VS Code.

        Supported step_config keys:
            - ``project``: Path to a project directory to open.
            - ``file``: Path to a specific file to open.
            - ``action``: Either ``open_project`` (default) or ``open_file``.
        """
        vscode = _get_vscode_module()
        action = step_config.get("action", "open_project")
        step_name = step_config.get("_step_name", "Open VS Code")

        if action == "open_project":
            project = step_config.get("project") or context.get("working_dir") or ""
            if not project:
                return self._failure(step_name, "No project path provided.")
            path = Path(project).expanduser().resolve()
            success = vscode.open_vscode(path)
            if success:
                return self._success(step_name, f"VS Code opened with project: {path}", output={"project": str(path)})
            return self._failure(step_name, f"Failed to open VS Code with project: {path}")

        elif action == "open_file":
            file_path = step_config.get("file", "")
            if not file_path:
                return self._failure(step_name, "No file path provided. Set 'file' in step config.")
            path = Path(file_path).expanduser().resolve()
            success = vscode.open_in_vscode(path)
            if success:
                return self._success(step_name, f"File opened in VS Code: {path}", output={"file": str(path)})
            return self._failure(step_name, f"Failed to open file in VS Code: {path}")

        return self._failure(step_name, f"Unknown action: {action}")

    def validate_config(self, step_config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        action = step_config.get("action", "open_project")
        if action == "open_project" and not step_config.get("project"):
            errors.append("'project' path is recommended for open_project action")
        if action == "open_file" and not step_config.get("file"):
            errors.append("'file' is required for open_file action")
        return errors


# Auto-register on import
default_registry.register(VSCodePlugin())
