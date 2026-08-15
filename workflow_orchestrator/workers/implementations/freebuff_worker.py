"""FreeBuff Desktop Worker — local AI worker executing via FreeBuff CLI or simulation.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from workflow_orchestrator.workers.desktop_worker import (
    DesktopWorker,
    DesktopWorkerTaskResult,
)

logger = logging.getLogger(__name__)


from workflow_orchestrator.integrations.transports.desktop_terminal_transport import DesktopTerminalTransport


class FreeBuffDesktopWorker(DesktopWorker):
    """Desktop AI worker wrapping FreeBuff CLI execution."""

    def __init__(self) -> None:
        super().__init__(
            worker_id="freebuff_desktop",
            name="FreeBuff Worker",
            skills=["codegen_general", "refactor_clean", "code_editing"],
            transport_type="cli_automation",
        )
        self.cli_path = shutil.which("freebuff") or "freebuff"
        self.terminal_transport = DesktopTerminalTransport(executable_name="freebuff")

    def discover(self) -> bool:
        """Check if FreeBuff CLI executable is installed."""
        return self.terminal_transport.is_available()

    def _execute_desktop_task(self, task_payload: Dict[str, Any]) -> DesktopWorkerTaskResult:
        """Execute task via FreeBuff CLI."""
        prompt = task_payload.get("prompt", "Execute FreeBuff task")
        project_root = Path(task_payload.get("workspace_dir", Path.cwd()))

        if not self.terminal_transport.is_available():
            err_msg = f"FreeBuff CLI executable ('{self.cli_path}') not found on system PATH."
            logger.warning(err_msg)
            return DesktopWorkerTaskResult(
                success=False,
                output_text=err_msg,
                error_message=err_msg,
                generated_files=[],
                metadata={"worker": "freebuff_desktop", "simulation_mode": True, "reason": "tool_not_installed"},
            )

        try:
            output = self.terminal_transport.send_prompt(prompt, cwd=project_root)
            return DesktopWorkerTaskResult(
                success=True,
                output_text=f"{output}\nTASK COMPLETE.",
                metadata={"worker": "freebuff_desktop", "simulation_mode": False},
            )
        except Exception as exc:
            err_msg = f"FreeBuff execution exception: {exc}"
            logger.warning(err_msg)
            return DesktopWorkerTaskResult(
                success=False,
                output_text=err_msg,
                error_message=str(exc),
                generated_files=[],
                metadata={"worker": "freebuff_desktop", "simulation_mode": False, "error": str(exc)},
            )
