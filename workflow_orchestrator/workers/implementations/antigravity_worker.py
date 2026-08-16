"""Antigravity Desktop Worker — local AI worker executing via Antigravity AGY CLI or direct execution.
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


class AntigravityDesktopWorker(DesktopWorker):
    """Desktop AI worker executing tasks via Google Antigravity (AGY) CLI or direct execution."""

    def __init__(self) -> None:
        super().__init__(
            worker_id="antigravity_desktop",
            name="Antigravity Worker",
            skills=["backend_api", "frontend_ui", "unit_testing", "deployment", "reasoning_architecture", "codegen_general", "fullstack_components", "code_editing"],
            transport_type="cli_automation",
        )
        self.cli_path = shutil.which("agy") or shutil.which("antigravity") or "agy"

    def discover(self) -> bool:
        """Check if Antigravity AGY CLI or ~/.gemini/antigravity environment is present."""
        found = shutil.which(self.cli_path)
        antigravity_dir = Path.home() / ".gemini" / "antigravity"
        return bool((found and os.path.exists(found)) or antigravity_dir.exists())

    def _execute_desktop_task(self, task_payload: Dict[str, Any]) -> DesktopWorkerTaskResult:
        """Execute task via Antigravity AGY CLI."""
        prompt = task_payload.get("prompt", "Execute Antigravity task")
        project_root = Path(task_payload.get("workspace_dir", Path.cwd()))

        found = shutil.which(self.cli_path)
        if not (found and os.path.exists(found)):
            err_msg = f"Antigravity CLI executable ('{self.cli_path}') not found on system PATH."
            logger.warning(err_msg)
            return DesktopWorkerTaskResult(
                success=False,
                output_text=err_msg,
                error_message=err_msg,
                generated_files=[],
                metadata={"worker": "antigravity_desktop", "simulation_mode": True, "reason": "tool_not_installed"},
            )

        cmd = [self.cli_path, "task", "run", "--prompt", prompt]

        # Track initial workspace files for generated_files detection
        before_files = get_workspace_snapshot(project_root)

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root), timeout=180)
            if res.returncode == 0:
                generated: List[Path] = []
                if project_root.exists():
                    for p in project_root.rglob("*"):
                        if p.is_file() and not any(part.startswith(".") for part in p.parts):
                            try:
                                if p not in before_files or p.stat().st_mtime > before_files[p]:
                                    generated.append(p)
                            except OSError:
                                pass

                return DesktopWorkerTaskResult(
                    success=True,
                    output_text=res.stdout or "Antigravity task completed successfully. TASK COMPLETE.",
                    generated_files=generated,
                    metadata={"worker": "antigravity_desktop", "simulation_mode": False},
                )

            err_text = res.stderr.strip() or res.stdout.strip() or f"Antigravity CLI process failed with exit code {res.returncode}"
            logger.warning("Antigravity CLI returned non-zero exit code %d: %s", res.returncode, err_text)
            return DesktopWorkerTaskResult(
                success=False,
                output_text=err_text,
                error_message=f"Process exited with code {res.returncode}",
                generated_files=[],
                metadata={"worker": "antigravity_desktop", "simulation_mode": False, "exit_code": res.returncode},
            )
        except Exception as exc:
            err_msg = f"Antigravity execution exception: {exc}"
            logger.warning(err_msg)
            return DesktopWorkerTaskResult(
                success=False,
                output_text=err_msg,
                error_message=str(exc),
                generated_files=[],
                metadata={"worker": "antigravity_desktop", "simulation_mode": False, "error": str(exc)},
            )
