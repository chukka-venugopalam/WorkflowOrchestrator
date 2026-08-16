"""Desktop Terminal Transport — PTY and process stream automation driver.

Drives local CLI agents (Claude Code CLI, OpenCode, Codex, Ollama) via zero-API process streams.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DesktopTerminalTransport:
    """Automates interactive PTY/CLI process streams for desktop workers."""

    def __init__(self, executable_name: str, default_args: Optional[List[str]] = None) -> None:
        self.executable_name = executable_name
        self.default_args = default_args or []
        self.binary_path = shutil.which(executable_name)
        self.process: Optional[subprocess.Popen] = None

    def is_available(self) -> bool:
        """Check if CLI tool binary is installed on system PATH."""
        return self.binary_path is not None or shutil.which(self.executable_name) is not None

    def start_session(self, cwd: Optional[Path] = None) -> bool:
        """Start local PTY / subprocess session for CLI agent."""
        if not self.is_available():
            logger.warning(f"Executable '{self.executable_name}' not found on PATH.")
            return False
        
        target_path = self.binary_path or self.executable_name
        target_cwd = str(cwd) if cwd else str(Path.cwd())

        try:
            self.process = subprocess.Popen(
                [target_path] + self.default_args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=target_cwd,
                shell=False,
            )
            logger.info(f"Started CLI process session for '{self.executable_name}' (PID: {self.process.pid})")
            return True
        except Exception as e:
            logger.error(f"Failed to start CLI process for '{self.executable_name}': {e}")
            return False

    def send_prompt(self, prompt: str, timeout_seconds: float = 30.0, cwd: Optional[Path] = None) -> str:
        """Dispatch prompt string to real process stdin/CLI command and capture actual output."""
        binary = self.binary_path or shutil.which(self.executable_name)
        if not binary:
            raise FileNotFoundError(
                f"Executable '{self.executable_name}' is not installed on system PATH. "
                "Please install the desktop application or CLI tool to enable real desktop worker execution."
            )

        target_cwd = str(cwd) if cwd else str(Path.cwd())
        cmd = [binary] + self.default_args

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="replace",
                cwd=target_cwd,
                shell=False,
            )
            try:
                stdout, stderr = proc.communicate(input=prompt, timeout=timeout_seconds)
                output = (stdout or stderr or "").strip()
                if not output and proc.returncode == 0:
                    output = f"Command '{self.executable_name}' executed cleanly (Exit code 0)."
                elif not output and proc.returncode != 0:
                    output = f"Command '{self.executable_name}' exited with code {proc.returncode}."
                return output
            except subprocess.TimeoutExpired:
                import sys
                if sys.platform == "win32":
                    try:
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, timeout=2.0)
                    except Exception:
                        proc.kill()
                else:
                    proc.kill()
                try:
                    stdout, stderr = proc.communicate(timeout=1.0)
                except Exception:
                    pass
                logger.warning(f"Real CLI command '{self.executable_name}' timed out after {timeout_seconds}s.")
                return f"Process '{self.executable_name}' timed out after {timeout_seconds} seconds."
        except Exception as e:
            logger.error(f"Real CLI execution error for '{self.executable_name}': {e}")
            raise RuntimeError(f"Real execution failed for '{self.executable_name}': {e}") from e

    def terminate_session(self) -> None:
        """Terminate process session."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2.0)
            except Exception:
                if self.process:
                    self.process.kill()
            self.process = None
