"""Plugin for Git operations (status, add, commit, push).

Wraps the existing ``modules/github.py`` module.
"""

from __future__ import annotations

from typing import Any

from workflow_orchestrator.models import StepResult, StepStatus
from workflow_orchestrator.plugins.base import Plugin, PluginMetadata
from workflow_orchestrator.plugins.registry import default_registry

_github_module = None


def _get_github_module():
    global _github_module
    if _github_module is None:
        from workflow_orchestrator.modules import github as _github_module
    return _github_module


class GitPlugin(Plugin):
    """Perform Git operations: status, add, commit, push, and full auto-push."""

    metadata = PluginMetadata(
        name="git",
        description="Perform Git operations: status, add, commit, push, or auto commit & push.",
        version="2.0.0",
    )

    def execute(
        self,
        step_config: dict[str, Any],
        context: dict[str, Any],
    ) -> StepResult:
        """Execute a Git action.

        Supported step_config keys:
            - ``action``: One of ``status``, ``add``, ``commit``, ``push``,
              ``auto_commit_push`` (default: ``auto_commit_push``).
            - ``message``: Commit message (for ``commit`` and ``auto_commit_push`` actions).
            - ``files``: List of files to stage (for ``add`` action).
        """
        git = _get_github_module()
        action = step_config.get("action", "auto_commit_push")
        step_name = step_config.get("_step_name", f"Git {action}")

        if action == "status":
            state = git.git_status()
            if state is None:
                return self._failure(step_name, "Not a Git repository or project directory not configured.")
            output = {
                "branch": state.branch,
                "has_changes": state.has_changes,
                "untracked": len(state.untracked_files),
                "modified": len(state.modified_files),
                "staged": len(state.staged_files),
                "ahead": state.ahead,
                "behind": state.behind,
            }
            return self._success(
                step_name,
                f"Branch: {state.branch}, Changes: {output['untracked'] + output['modified'] + output['staged']}",
                output=output,
            )

        elif action == "add":
            files = step_config.get("files")
            success = git.git_add(files)
            if success:
                return self._success(step_name, "Files staged successfully.")
            return self._failure(step_name, "Failed to stage files.")

        elif action == "commit":
            message = step_config.get("message", "")
            success = git.git_commit(message)
            if success:
                return self._success(step_name, f"Committed: {message or 'auto-generated'}")
            return self._failure(step_name, "Commit failed or nothing to commit.")

        elif action == "push":
            branch = step_config.get("branch")
            success = git.git_push(branch)
            if success:
                return self._success(step_name, f"Pushed to origin/{branch or 'current branch'}")
            return self._failure(step_name, "Push failed.")

        elif action == "auto_commit_push":
            message = step_config.get("message")
            success = git.auto_commit_and_push(message)
            if success:
                return self._success(step_name, "Changes committed and pushed successfully.")
            return self._failure(step_name, "Git auto commit & push failed.")

        return self._failure(step_name, f"Unknown Git action: {action}")

    def validate_config(self, step_config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        valid_actions = {"status", "add", "commit", "push", "auto_commit_push"}
        action = step_config.get("action", "auto_commit_push")
        if action not in valid_actions:
            errors.append(f"Unknown git action: {action}. Valid: {', '.join(sorted(valid_actions))}")
        return errors


# Auto-register on import
default_registry.register(GitPlugin())
