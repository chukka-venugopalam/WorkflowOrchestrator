"""Cursor IDE Desktop Worker — local IDE AI worker operating without cloud API keys.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from workflow_orchestrator.workers.desktop_worker import (
    DesktopWorker,
    DesktopWorkerTaskResult,
)
from workflow_orchestrator.integrations.transports.desktop_ui_transport import DesktopUITransport

logger = logging.getLogger(__name__)


class CursorDesktopWorker(DesktopWorker):
    """Desktop AI worker wrapping Cursor IDE via UI & Clipboard automation."""

    def __init__(self) -> None:
        super().__init__(
            worker_id="cursor_desktop",
            name="Cursor IDE Worker",
            skills=["frontend_ui", "fullstack_components", "code_editing"],
            transport_type="ui_automation",
        )
        self.ui_transport = DesktopUITransport(target_window_title="Cursor")

    def discover(self) -> bool:
        """Check if Cursor IDE is installed or running."""
        return self.ui_transport.is_available()

    def _execute_desktop_task(self, task_payload: Dict[str, Any]) -> DesktopWorkerTaskResult:
        """Execute task via IDE UI Automation and Clipboard Sync."""
        prompt = task_payload.get("prompt", "Execute IDE task")
        project_root = Path(task_payload.get("workspace_dir", Path.cwd()))
        
        self.ui_transport.dispatch_prompt_to_ide(prompt)
        modified_files = self.ui_transport.capture_editor_diff(project_root)

        return DesktopWorkerTaskResult(
            success=True,
            output_text=f"Cursor IDE task completed. Modified files count: {len(modified_files)}",
            generated_files=modified_files,
            metadata={"worker": "cursor_desktop", "transport": "ui_automation"},
        )
