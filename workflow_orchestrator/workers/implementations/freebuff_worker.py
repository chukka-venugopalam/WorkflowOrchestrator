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
        """Execute task via FreeBuff CLI."""
        prompt = task_payload.get("prompt", "Execute FreeBuff task")
        project_root = Path(task_payload.get("workspace_dir", Path.cwd()))

        found = shutil.which(self.cli_path)
        if not (found and os.path.exists(found)):
            err_msg = f"FreeBuff CLI executable ('{self.cli_path}') not found on system PATH."
            logger.warning(err_msg)
            return DesktopWorkerTaskResult(
                success=False,
                output_text=err_msg,
                error_message=err_msg,
                generated_files=[],
                metadata={"worker": "freebuff_desktop", "simulation_mode": True, "reason": "tool_not_installed"},
            )

        cmd = [self.cli_path, prompt]

        # Track initial workspace files for generated_files detection
        before_files = {}
        if project_root.exists():
            for p in project_root.rglob("*"):
                if p.is_file() and not any(part.startswith(".") for part in p.parts):
                    try:
                        before_files[p] = p.stat().st_mtime
                    except OSError:
                        pass

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root), timeout=120)
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
                    output_text=res.stdout or "FreeBuff task completed successfully.",
                    generated_files=generated,
                    metadata={"worker": "freebuff_desktop", "simulation_mode": False},
                )

            err_text = res.stderr.strip() or res.stdout.strip() or f"FreeBuff CLI process failed with exit code {res.returncode}"
            logger.warning("FreeBuff CLI returned non-zero exit code %d: %s", res.returncode, err_text)
            return DesktopWorkerTaskResult(
                success=False,
                output_text=err_text,
                error_message=f"Process exited with code {res.returncode}",
                generated_files=[],
                metadata={"worker": "freebuff_desktop", "simulation_mode": False, "exit_code": res.returncode},
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
