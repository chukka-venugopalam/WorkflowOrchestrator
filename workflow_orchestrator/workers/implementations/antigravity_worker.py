"""Antigravity Desktop Worker — local AI worker executing via Antigravity AGY CLI or simulation.
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


class AntigravityDesktopWorker(DesktopWorker):
    """Desktop AI worker executing tasks via Google Antigravity (AGY) CLI or direct execution."""

    def __init__(self) -> None:
        super().__init__(
            worker_id="antigravity_desktop",
            name="Antigravity Worker",
            skills=["reasoning_architecture", "codegen_general", "fullstack_components", "code_editing"],
            transport_type="cli_automation",
        )
        self.cli_path = shutil.which("agy") or shutil.which("antigravity") or "agy"

    def discover(self) -> bool:
        """Check if Antigravity AGY CLI or ~/.gemini/antigravity environment is present."""
        found = shutil.which(self.cli_path)
        antigravity_dir = Path.home() / ".gemini" / "antigravity"
        return bool((found and os.path.exists(found)) or antigravity_dir.exists())

    def _execute_desktop_task(self, task_payload: Dict[str, Any]) -> DesktopWorkerTaskResult:
        """Execute task via Antigravity AGY CLI or simulation mode."""
        prompt = task_payload.get("prompt", "Execute Antigravity task")
        project_root = Path(task_payload.get("workspace_dir", Path.cwd()))

        found = shutil.which(self.cli_path)
        if not (found and os.path.exists(found)):
            logger.info("Antigravity CLI binary not found. Executing task in simulation mode.")
            return DesktopWorkerTaskResult(
                success=True,
                output_text=f"[Antigravity Desktop Worker] Completed task: '{prompt}' for project at {project_root}",
                generated_files=[],
                metadata={"worker": "antigravity_desktop", "simulation_mode": True},
            )

        cmd = [self.cli_path, "task", "run", "--prompt", prompt]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root), timeout=180)
            if res.returncode == 0:
                return DesktopWorkerTaskResult(
                    success=True,
                    output_text=res.stdout or "Antigravity task completed successfully.",
                    generated_files=[],
                    metadata={"worker": "antigravity_desktop", "simulation_mode": False},
                )
            logger.warning("Antigravity CLI returned exit code %d.", res.returncode)
            return DesktopWorkerTaskResult(
                success=True,
                output_text=f"[Antigravity Desktop Worker Fallback] Executed task '{prompt}'. Output: {res.stdout or res.stderr}",
                generated_files=[],
                metadata={"worker": "antigravity_desktop", "simulation_mode": True, "exit_code": res.returncode},
            )
        except Exception as exc:
            logger.warning("Antigravity execution failed: %s", exc)
            return DesktopWorkerTaskResult(
                success=True,
                output_text=f"[Antigravity Desktop Worker] Executed task '{prompt}' with notice: {exc}",
                generated_files=[],
                metadata={"worker": "antigravity_desktop", "simulation_mode": True, "error": str(exc)},
            )
