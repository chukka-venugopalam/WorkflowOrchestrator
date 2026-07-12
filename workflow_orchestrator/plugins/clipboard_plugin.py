"""Plugin for clipboard operations (copy, paste).

Wraps the existing ``modules/clipboard.py`` module.
"""

from __future__ import annotations

from typing import Any

from workflow_orchestrator.models import StepResult, StepStatus
from workflow_orchestrator.plugins.base import Plugin, PluginMetadata
from workflow_orchestrator.plugins.registry import default_registry

_clipboard_module = None


def _get_clipboard_module():
    global _clipboard_module
    if _clipboard_module is None:
        from workflow_orchestrator.modules import clipboard as _clipboard_module
    return _clipboard_module


class ClipboardPlugin(Plugin):
    """Copy text to or read text from the system clipboard."""

    metadata = PluginMetadata(
        name="clipboard",
        description="Copy text to or read text from the system clipboard.",
        version="2.0.0",
    )

    def execute(
        self,
        step_config: dict[str, Any],
        context: dict[str, Any],
    ) -> StepResult:
        """Perform a clipboard action.

        Supported step_config keys:
            - ``action``: ``copy`` (default) or ``paste``.
            - ``text``: Text to copy (for ``copy`` action). If omitted,
              reads from ``context.get('clipboard_text', '')``.
        """
        clipboard = _get_clipboard_module()
        action = step_config.get("action", "copy")
        step_name = step_config.get("_step_name", f"Clipboard {action}")

        if action == "copy":
            text = step_config.get("text") or context.get("clipboard_text", "")
            if not text:
                return self._failure(step_name, "No text provided to copy.")
            success = clipboard.copy_to_clipboard(text)
            if success:
                return self._success(
                    step_name,
                    f"Copied {len(text)} characters to clipboard.",
                    output={"length": len(text), "preview": text[:80]},
                )
            return self._failure(step_name, "Failed to copy to clipboard.")

        elif action == "paste":
            text = clipboard.read_from_clipboard()
            if text is not None:
                return self._success(
                    step_name,
                    f"Read {len(text)} characters from clipboard.",
                    output={"text": text, "length": len(text)},
                )
            return self._failure(step_name, "Failed to read from clipboard.")

        return self._failure(step_name, f"Unknown clipboard action: {action}")


# Auto-register on import
default_registry.register(ClipboardPlugin())
