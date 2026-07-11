"""Terminal command execution for the Workflow Orchestrator.

Provides a safe and consistent interface for running shell commands,
capturing output, and handling errors gracefully.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from modules.logger import logger


@dataclass
class CommandResult:
    """Result of a terminal command execution.

    Attributes:
        stdout: Standard output from the command.
        stderr: Standard error from the command.
        exit_code: Return code (0 typically means success).
        success: True if exit_code is 0.
    """

    stdout: str
    stderr: str
    exit_code: int

    @property
    def success(self) -> bool:
        """Check if the command completed successfully."""
        return self.exit_code == 0


def run_command(
    command: str,
    cwd: Optional[Path] = None,
    shell: bool = True,
    timeout: Optional[int] = 60,
    env: Optional[dict] = None,
) -> CommandResult:
    """Execute a terminal command and capture its output.

    Args:
        command: The shell command string to execute.
        cwd: Working directory for the command. Defaults to current directory.
        shell: Whether to run the command through a shell. Defaults to True.
        timeout: Maximum execution time in seconds. None means no timeout.
        env: Optional dictionary of environment variables to set.

    Returns:
        CommandResult: Object containing stdout, stderr, and exit code.

    Raises:
        subprocess.TimeoutExpired: If the command exceeds the timeout.
    """
    logger.info("Running command: %s", command)
    if cwd:
        logger.debug("Working directory: %s", cwd)

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=shell,
            cwd=str(cwd) if cwd else None,
            timeout=timeout,
            env=env,
        )

        cmd_result = CommandResult(
            stdout=result.stdout.strip(),
            stderr=result.stderr.strip(),
            exit_code=result.returncode,
        )

        if cmd_result.success:
            logger.debug("Command succeeded. stdout: %s", cmd_result.stdout[:200])
        else:
            logger.warning(
                "Command failed (exit code %d). stderr: %s",
                cmd_result.exit_code,
                cmd_result.stderr[:200],
            )

        return cmd_result

    except subprocess.TimeoutExpired:
        logger.error("Command timed out after %d seconds: %s", timeout, command)
        return CommandResult(
            stdout="",
            stderr=f"Command timed out after {timeout} seconds.",
            exit_code=-1,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("Failed to execute command: %s", exc)
        return CommandResult(
            stdout="",
            stderr=str(exc),
            exit_code=-1,
        )


def run_command_async(command: str, cwd: Optional[Path] = None) -> subprocess.Popen:
    """Launch a command asynchronously without waiting for completion.

    Useful for opening applications like VS Code or a browser
    where we don't need to wait for the process to exit.

    Args:
        command: The command string to execute.
        cwd: Working directory for the command.

    Returns:
        subprocess.Popen: The running process handle.
    """
    logger.info("Launching async command: %s", command)
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.debug("Async command launched with PID %d", process.pid)
        return process
    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("Failed to launch async command: %s", exc)
        raise
