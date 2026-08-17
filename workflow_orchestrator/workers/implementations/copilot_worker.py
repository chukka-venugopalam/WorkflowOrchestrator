"""GitHub Copilot Desktop Worker — local IDE AI worker operating without cloud API keys.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from workflow_orchestrator.workers.desktop_worker import (
    DesktopWorker,
    DesktopWorkerTaskResult,
)
from workflow_orchestrator.integrations.transports.desktop_ui_transport import DesktopUITransport

logger = logging.getLogger(__name__)


class CopilotDesktopWorker(DesktopWorker):
    """Desktop AI worker wrapping GitHub Copilot via VS Code Automation."""

    def __init__(self) -> None:
        super().__init__(
            worker_id="copilot_desktop",
            name="GitHub Copilot Worker",
            skills=["unit_testing", "inline_completion", "refactoring"],
            transport_type="ui_automation",
        )
        self.ui_transport = DesktopUITransport(target_window_title="Visual Studio Code")

    def discover(self) -> bool:
        """Check if VS Code executable or Copilot extension is installed."""
        import shutil
        import os
        from pathlib import Path
        if shutil.which("code") or shutil.which("code.cmd"):
            return True
        ext_dir = Path.home() / ".vscode" / "extensions"
        if ext_dir.exists():
            try:
                if any("copilot" in p.name.lower() for p in ext_dir.iterdir() if p.is_dir()):
                    return True
            except Exception:
                pass
        return False

    def _execute_desktop_task(self, task_payload: Dict[str, Any]) -> DesktopWorkerTaskResult:
        prompt = task_payload.get("prompt", "Generate Unit Tests")
        try:
            output_text, meta = self.ui_transport.capture_response(prompt, timeout_seconds=30.0)
            if not output_text or output_text.strip().startswith(("Error", "Failed", "[Error]")):
                raise RuntimeError("Captured response from VS Code / GitHub Copilot GUI was empty or an error message")

            logger.info("Captured real GitHub Copilot Desktop response (%d chars): %r", len(output_text), output_text[:200])
            return DesktopWorkerTaskResult(
                success=True,
                output_text=output_text,
                metadata={"worker": "copilot_desktop", "transport": "ui_automation", **meta},
            )
        except Exception as exc:
            err_msg = f"GitHub Copilot UI automation capture failed: {exc}"
            logger.warning(err_msg)
            return DesktopWorkerTaskResult(
                success=False,
                output_text=err_msg,
                error_message=str(exc),
                generated_files=[],
                metadata={"worker": "copilot_desktop", "transport": "ui_automation", "error": str(exc)},
            )
