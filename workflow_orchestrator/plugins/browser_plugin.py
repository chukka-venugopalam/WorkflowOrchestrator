"""Plugin for opening URLs in the browser.

Wraps the existing ``modules/browser.py`` module.
Supports opening any URL, as well as specific shortcuts
for GitHub, Render, and Vercel dashboards.
"""

from __future__ import annotations

from typing import Any

from workflow_orchestrator.models import StepResult, StepStatus
from workflow_orchestrator.plugins.base import Plugin, PluginMetadata
from workflow_orchestrator.plugins.registry import default_registry

# Lazy imports to avoid circular dependencies
_browser_module = None


def _get_browser_module():
    global _browser_module
    if _browser_module is None:
        from workflow_orchestrator.modules import browser as _browser_module
    return _browser_module


class BrowserPlugin(Plugin):
    """Open URLs in the configured web browser."""

    metadata = PluginMetadata(
        name="browser",
        description="Open URLs in the configured web browser. Supports open_url, open_github, open_render, open_vercel.",
        version="2.0.0",
    )

    def execute(
        self,
        step_config: dict[str, Any],
        context: dict[str, Any],
    ) -> StepResult:
        """Execute a browser action.

        Supported step_config keys:
            - ``action``: One of ``open_url``, ``open_github``, ``open_render``,
              ``open_render_logs``, ``open_vercel`` (default: ``open_url``).
            - ``url``: URL to open (required for ``open_url`` action).
        """
        browser = _get_browser_module()
        action = step_config.get("action", "open_url")
        url = step_config.get("url", "")

        if action == "open_github":
            return self._wrap_result("Open GitHub", browser.open_github())
        elif action == "open_render":
            return self._wrap_result("Open Render", browser.open_render())
        elif action == "open_render_logs":
            return self._wrap_result("Open Render Logs", browser.open_render_logs())
        elif action == "open_vercel":
            return self._wrap_result("Open Vercel", browser.open_vercel())
        elif action == "open_url":
            resolved_url = url or context.get("url", "")
            if not resolved_url:
                return self._failure(
                    step_config.get("_step_name", "Open URL"),
                    "No URL provided. Set 'url' in step config or pass it via context.",
                )
            return self._wrap_result(f"Open URL: {resolved_url}", browser.open_url(resolved_url))
        else:
            return self._failure(
                step_config.get("_step_name", "Browser"),
                f"Unknown browser action: {action}. "
                f"Supported: open_url, open_github, open_render, open_render_logs, open_vercel",
            )

    def _wrap_result(self, step_name: str, success: bool) -> StepResult:
        if success:
            return self._success(step_name, f"{step_name}: Browser opened successfully.")
        return self._failure(step_name, f"{step_name}: Failed to open browser.")

    def validate_config(self, step_config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        action = step_config.get("action", "open_url")
        if action == "open_url" and not step_config.get("url"):
            errors.append("'url' is required when action is 'open_url'")
        if action not in ("open_url", "open_github", "open_render", "open_render_logs", "open_vercel"):
            errors.append(f"Unknown action: {action}")
        return errors


# Auto-register on import
default_registry.register(BrowserPlugin())
