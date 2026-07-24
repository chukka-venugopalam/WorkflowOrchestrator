"""CLI command transport implementation — executes commands via subprocess.

Supports running local CLI commands, capturing output, and cancellation.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from workflow_orchestrator.transports.cli_transport import CliTransport
from workflow_orchestrator.transports.transport import (
    TransportError,
    TransportRequest,
    TransportResponse,
)

logger = logging.getLogger(__name__)


class CliCommandTransport(CliTransport):
    """CLI command transport implementation using asyncio subprocess.

    Executes shell commands and captures stdout/stderr output.
    Supports cancellation via process termination.
    """

    def __init__(self, shell: bool = True, cwd: str | None = None) -> None:
        """Initialize the CLI command transport.

        Args:
            shell: Whether to run commands through a shell.
            cwd: Working directory for command execution.
        """
        self._shell = shell
        self._cwd = cwd
        self._active_processes: dict[str, asyncio.subprocess.Process] = {}

    async def send(self, request: TransportRequest) -> TransportResponse:
        """Execute a CLI command and capture output.

        Args:
            request: Transport request with command in body or URL field.

        Returns:
            TransportResponse with stdout as body.
        """
        start_time = time.time()
        command = request.body or request.url

        if not command:
            raise TransportError(
                message="No command specified",
                transport_type="cli_command",
                recoverable=False,
            )

        try:
            proc = await asyncio.create_subprocess_shell(
                command if self._shell else command,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._cwd,
            )

            request_id = request.url or command[:20]
            self._active_processes[request_id] = proc

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=request.timeout_seconds or 30,
            )

            self._active_processes.pop(request_id, None)
            duration_ms = (time.time() - start_time) * 1000

            output = stdout.decode("utf-8", errors="replace")
            error_output = stderr.decode("utf-8", errors="replace")

            return TransportResponse(
                status_code=proc.returncode or 0,
                body=output,
                duration_ms=duration_ms,
                success=proc.returncode == 0,
                error=error_output if proc.returncode != 0 else "",
            )
        except asyncio.TimeoutError:
            # Cancel the process
            if request_id := request.url or command[:20]:
                proc = self._active_processes.get(request_id)
                if proc:
                    proc.terminate()
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        proc.kill()
                    self._active_processes.pop(request_id, None)
            raise TransportError(
                message=f"Command timed out after {request.timeout_seconds}s",
                transport_type="cli_command",
                recoverable=True,
                retryable=True,
            )
        except Exception as exc:
            raise TransportError(
                message=str(exc),
                transport_type="cli_command",
                recoverable=True,
                retryable=True,
            ) from exc

    async def cancel(self, request_id: str) -> None:
        """Cancel a running command.

        Args:
            request_id: The request/command identifier.
        """
        proc = self._active_processes.get(request_id)
        if proc and proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                proc.kill()
            self._active_processes.pop(request_id, None)
            logger.debug("Cancelled CLI command '%s'", request_id)

    async def health(self) -> bool:
        """Check if the transport can execute commands.

        Returns:
            True if basic shell access works.
        """
        import sys
        try:
            cmd = f'"{sys.executable}" -c "print(\'ok\')"'
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
            return proc.returncode == 0
        except Exception:
            return False

    @property
    def transport_type(self) -> str:
        """Human-readable transport type identifier."""
        return "cli_command"
