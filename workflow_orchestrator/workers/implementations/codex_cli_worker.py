"""Codex CLI Desktop Worker — OpenAI Codex command-line worker operating via Codex CLI.
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


class CodexCLIDesktopWorker(DesktopWorker):
    """Desktop AI worker wrapping OpenAI Codex CLI for code generation and task execution."""

    def __init__(self) -> None:
        super().__init__(
            worker_id="codex_cli_desktop",
            name="Codex CLI Worker",
            skills=["codegen_general", "codegen_python", "codegen_typescript", "reasoning_analysis"],
            transport_type="cli_automation",
        )
        self.cli_path = shutil.which("codex") or "codex"

    def discover(self) -> bool:
        """Check if Codex CLI binary is installed on system PATH."""
        found = shutil.which(self.cli_path)
        return bool(found and os.path.exists(found))

    def _execute_desktop_task(self, task_payload: Dict[str, Any]) -> DesktopWorkerTaskResult:
        """Execute task via OpenAI Codex CLI."""
        prompt = task_payload.get("prompt", "Execute task with Codex CLI")
        project_root = Path(task_payload.get("workspace_dir", Path.cwd()))

        found = shutil.which(self.cli_path)
        if not (found and os.path.exists(found)):
            err_msg = f"Codex CLI executable ('{self.cli_path}') not found on system PATH."
            logger.warning(err_msg)
            return DesktopWorkerTaskResult(
                success=False,
                output_text=err_msg,
                error_message=err_msg,
                generated_files=[],
                metadata={"worker": "codex_cli_desktop", "reason": "tool_not_installed"},
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
                    output_text=res.stdout or "Codex CLI task completed successfully.",
                    generated_files=generated,
                    metadata={"worker": "codex_cli_desktop"},
                )

            err_text = res.stderr.strip() or res.stdout.strip() or f"Codex CLI process failed with exit code {res.returncode}"
            logger.warning("Codex CLI returned non-zero exit code %d: %s", res.returncode, err_text)
            return DesktopWorkerTaskResult(
                success=False,
                output_text=err_text,
                error_message=f"Process exited with code {res.returncode}",
                generated_files=[],
                metadata={"worker": "codex_cli_desktop", "exit_code": res.returncode},
            )
        except Exception as exc:
            err_msg = f"Codex CLI execution exception: {exc}"
            logger.warning(err_msg)
            return DesktopWorkerTaskResult(
                success=False,
                output_text=err_msg,
                error_message=str(exc),
                generated_files=[],
                metadata={"worker": "codex_cli_desktop", "error": str(exc)},
            )
