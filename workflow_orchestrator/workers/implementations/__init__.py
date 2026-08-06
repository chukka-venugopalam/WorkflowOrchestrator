"""Desktop Worker Implementations Package.

Exposes concrete desktop worker classes wrapping local CLI, IDE, and Web AI tools.
"""

from __future__ import annotations

from workflow_orchestrator.workers.implementations.claude_code_worker import ClaudeCodeDesktopWorker
from workflow_orchestrator.workers.implementations.cursor_worker import CursorDesktopWorker
from workflow_orchestrator.workers.implementations.copilot_worker import CopilotDesktopWorker
from workflow_orchestrator.workers.implementations.opencode_worker import OpenCodeDesktopWorker
from workflow_orchestrator.workers.implementations.ollama_worker import OllamaDesktopWorker
from workflow_orchestrator.workers.implementations.optional_web_worker import OptionalWebDesktopWorker
from workflow_orchestrator.workers.implementations.antigravity_worker import AntigravityDesktopWorker
from workflow_orchestrator.workers.implementations.freebuff_worker import FreeBuffDesktopWorker

__all__ = [
    "ClaudeCodeDesktopWorker",
    "CursorDesktopWorker",
    "CopilotDesktopWorker",
    "OpenCodeDesktopWorker",
    "OllamaDesktopWorker",
    "OptionalWebDesktopWorker",
    "AntigravityDesktopWorker",
    "FreeBuffDesktopWorker",
]
