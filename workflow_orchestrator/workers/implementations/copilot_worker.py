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
        self.ui_transport.dispatch_prompt_to_ide(prompt)
        return DesktopWorkerTaskResult(
            success=True,
            output_text=f"GitHub Copilot task completed: {prompt[:80]}",
            metadata={"worker": "copilot_desktop", "transport": "ui_automation"},
        )
