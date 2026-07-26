"""OpenCode Desktop Worker — local CLI AI worker operating without cloud API keys.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from workflow_orchestrator.workers.desktop_worker import (
    DesktopWorker,
    DesktopWorkerTaskResult,
)
from workflow_orchestrator.integrations.transports.desktop_terminal_transport import DesktopTerminalTransport

logger = logging.getLogger(__name__)


class OpenCodeDesktopWorker(DesktopWorker):
    """Desktop AI worker wrapping OpenCode CLI via PTY stream automation."""

    def __init__(self) -> None:
        super().__init__(
            worker_id="opencode_desktop",
            name="OpenCode Worker",
            skills=["backend_api", "deployment", "testing", "cli_automation"],
            transport_type="terminal",
        )
        self.terminal_transport = DesktopTerminalTransport(executable_name="opencode")

    def discover(self) -> bool:
        return self.terminal_transport.is_available()

    def _execute_desktop_task(self, task_payload: Dict[str, Any]) -> DesktopWorkerTaskResult:
        prompt = task_payload.get("prompt", "Execute task")
        output = self.terminal_transport.send_prompt(prompt)
        return DesktopWorkerTaskResult(
            success=True,
            output_text=output,
            metadata={"worker": "opencode_desktop", "transport": "terminal"},
        )
