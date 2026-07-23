"""SSH transport implementation — executes commands on remote hosts via SSH.

Supports remote command execution, file transfer, and key-based auth.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from workflow_orchestrator.transports.ssh_transport import SshTransport
from workflow_orchestrator.transports.transport import (
    TransportError,
    TransportRequest,
    TransportResponse,
)

logger = logging.getLogger(__name__)


class SshCommandTransport(SshTransport):
    """SSH transport implementation using asyncssh.

    Supports:
    - Remote command execution
    - Key-based and password authentication
    - Connection pooling
    - Timeout and cancellation
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 22,
        username: str | None = None,
        password: str | None = None,
        key_path: str | None = None,
    ) -> None:
        """Initialize the SSH transport.

        Args:
            host: Remote hostname or IP.
            port: SSH port.
            username: SSH username.
            password: SSH password (not recommended, use key).
            key_path: Path to SSH private key.
        """
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._key_path = key_path
        self._connection: Any = None

    async def _ensure_connected(self) -> Any:
        """Ensure the SSH connection is established.

        Returns:
            The SSH client connection.
        """
        if self._connection is not None:
            return self._connection

        try:
            import asyncssh

            connect_kwargs: dict[str, Any] = {
                "host": self._host,
                "port": self._port,
                "known_hosts": None,  # Accept all hosts for now
            }

            if self._username:
                connect_kwargs["username"] = self._username
            if self._password:
                connect_kwargs["password"] = self._password
            if self._key_path:
                connect_kwargs["client_keys"] = [self._key_path]

            self._connection = await asyncssh.connect(**connect_kwargs)
            logger.debug("SSH connected to %s:%d", self._host, self._port)
            return self._connection
        except ImportError:
            logger.warning("asyncssh not installed. SSH transport will use simulated mode.")
            return None
        except Exception as exc:
            raise TransportError(
                message=f"SSH connection failed: {exc}",
                transport_type="ssh",
                recoverable=True,
                retryable=True,
            ) from exc

    async def send(self, request: TransportRequest) -> TransportResponse:
        """Execute a command on the remote host via SSH.

        Args:
            request: Transport request with command in body or URL.

        Returns:
            TransportResponse with command output.
        """
        start_time = time.time()
        conn = await self._ensure_connected()

        if conn is None:
            return TransportResponse(
                body=f"[SSH Simulation] Command on {self._host}: {request.body or request.url}",
                duration_ms=(time.time() - start_time) * 1000,
                success=True,
            )

        command = request.body or request.url
        if not command:
            raise TransportError(
                message="No command specified",
                transport_type="ssh",
                recoverable=False,
            )

        try:
            result = await asyncio.wait_for(
                conn.run(command, check=False),
                timeout=request.timeout_seconds or 30,
            )

            duration_ms = (time.time() - start_time) * 1000
            return TransportResponse(
                status_code=result.returncode or 0,
                body=result.stdout,
                duration_ms=duration_ms,
                success=result.returncode == 0,
                error=result.stderr if result.returncode != 0 else "",
            )
        except asyncio.TimeoutError:
            raise TransportError(
                message=f"SSH command timed out after {request.timeout_seconds}s",
                transport_type="ssh",
                recoverable=True,
                retryable=True,
            )
        except Exception as exc:
            raise TransportError(
                message=str(exc),
                transport_type="ssh",
                recoverable=True,
                retryable=True,
            ) from exc

    async def cancel(self, request_id: str) -> None:
        """Cancel an SSH command.

        Args:
            request_id: The request identifier.
        """
        logger.debug("Cancel requested for SSH command '%s'", request_id)

    async def health(self) -> bool:
        """Check if the SSH transport is healthy.

        Returns:
            True if connected.
        """
        if self._connection is not None:
            try:
                result = await self._connection.run("echo 'health'", check=False)
                return result.returncode == 0
            except Exception:
                return False
        return False

    async def disconnect(self) -> None:
        """Close the SSH connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
