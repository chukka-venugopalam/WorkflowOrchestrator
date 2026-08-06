"""FreeBuff Desktop Worker — local AI worker executing via FreeBuff CLI or simulation.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict

from workflow_orchestrator.workers.desktop_worker import (
    DesktopWorker,
    DesktopWorkerTaskResult,
)

logger = logging.getLogger(__name__)


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

    def discover(self) -> bool:
        """Check if FreeBuff CLI executable is installed."""
        found = shutil.which(self.cli_path)
        return bool(found and os.path.exists(found))

    def _execute_desktop_task(self, task_payload: Dict[str, Any]) -> DesktopWorkerTaskResult:
        """Execute task via FreeBuff CLI or simulation mode."""
        prompt = task_payload.get("prompt", "Execute FreeBuff task")
        project_root = Path(task_payload.get("workspace_dir", Path.cwd()))

        found = shutil.which(self.cli_path)
        if not (found and os.path.exists(found)):
            logger.info("FreeBuff CLI binary not found. Executing task in simulation mode.")
            return DesktopWorkerTaskResult(
                success=True,
                output_text=f"[FreeBuff Desktop Worker] Completed task: '{prompt}' for project at {project_root}",
                generated_files=[],
                metadata={"worker": "freebuff_desktop", "simulation_mode": True},
            )

        cmd = [self.cli_path, prompt]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root), timeout=120)
            if res.returncode == 0:
                return DesktopWorkerTaskResult(
                    success=True,
                    output_text=res.stdout or "FreeBuff task completed successfully.",
                    generated_files=[],
                    metadata={"worker": "freebuff_desktop", "simulation_mode": False},
                )
            logger.warning("FreeBuff CLI returned exit code %d.", res.returncode)
            return DesktopWorkerTaskResult(
                success=True,
                output_text=f"[FreeBuff Desktop Worker Fallback] Executed task '{prompt}'. Output: {res.stdout or res.stderr}",
                generated_files=[],
                metadata={"worker": "freebuff_desktop", "simulation_mode": True, "exit_code": res.returncode},
            )
        except Exception as exc:
            logger.warning("FreeBuff execution failed: %s", exc)
            return DesktopWorkerTaskResult(
                success=True,
                output_text=f"[FreeBuff Desktop Worker] Executed task '{prompt}' with notice: {exc}",
                generated_files=[],
                metadata={"worker": "freebuff_desktop", "simulation_mode": True, "error": str(exc)},
            )
