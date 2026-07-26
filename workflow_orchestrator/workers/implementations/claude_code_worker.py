"""Claude Code Desktop Worker — local CLI AI worker operating without cloud API keys.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from workflow_orchestrator.workers.desktop_worker import (
    DesktopWorker,
    DesktopWorkerTaskResult,
    SkillCapability,
)
from workflow_orchestrator.integrations.transports.desktop_terminal_transport import DesktopTerminalTransport

logger = logging.getLogger(__name__)


class ClaudeCodeDesktopWorker(DesktopWorker):
    """Desktop AI worker wrapping Claude Code CLI via PTY stream automation."""

    def __init__(self) -> None:
        super().__init__(
            worker_id="claude_code_desktop",
            name="Claude Code CLI Worker",
            skills=["backend_api", "architecture", "refactoring", "git_ops"],
            transport_type="terminal",
        )
        self.terminal_transport = DesktopTerminalTransport(
            executable_name="claude",
            default_args=["--no-interactive"],
        )

    def discover(self) -> bool:
        """Check if Claude Code CLI is available on local PATH."""
        return self.terminal_transport.is_available()

    def _execute_desktop_task(self, task_payload: Dict[str, Any]) -> DesktopWorkerTaskResult:
        """Execute task via local terminal PTY transport."""
        prompt = task_payload.get("prompt", "Execute task")
        output = self.terminal_transport.send_prompt(prompt)
        return DesktopWorkerTaskResult(
            success=True,
            output_text=output,
            metadata={"worker": "claude_code_desktop", "transport": "terminal"},
        )
