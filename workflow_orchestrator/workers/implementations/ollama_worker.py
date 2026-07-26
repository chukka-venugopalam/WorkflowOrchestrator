"""Ollama Local Desktop Worker — offline local LLM worker operating without cloud API keys.
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


class OllamaDesktopWorker(DesktopWorker):
    """Desktop AI worker wrapping Ollama Local Engine via local execution."""

    def __init__(self, model_name: str = "codellama") -> None:
        super().__init__(
            worker_id="ollama_desktop",
            name=f"Ollama Local Engine ({model_name})",
            skills=["local_inference", "fast_completion", "offline_edit"],
            transport_type="terminal",
        )
        self.model_name = model_name
        self.terminal_transport = DesktopTerminalTransport(
            executable_name="ollama",
            default_args=["run", model_name],
        )

    def discover(self) -> bool:
        """Check if local Ollama HTTP service or CLI is active."""
        if self.terminal_transport.is_available():
            return True
        try:
            import urllib.request
            req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _execute_desktop_task(self, task_payload: Dict[str, Any]) -> DesktopWorkerTaskResult:
        prompt = task_payload.get("prompt", "Execute task")
        
        # Try local HTTP API endpoint first
        try:
            import json
            import urllib.request
            data = json.dumps({"model": self.model_name, "prompt": prompt, "stream": False}).encode("utf-8")
            req = urllib.request.Request(
                "http://127.0.0.1:11434/api/generate",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                res_body = json.loads(resp.read().decode("utf-8"))
                output = res_body.get("response", "")
                return DesktopWorkerTaskResult(
                    success=True,
                    output_text=output or "Local Ollama generation completed cleanly.",
                    metadata={"worker": "ollama_desktop", "model": self.model_name, "mode": "http_api"},
                )
        except Exception as e:
            # Fallback to CLI transport if available
            if self.terminal_transport.is_available():
                output = self.terminal_transport.send_prompt(prompt)
                return DesktopWorkerTaskResult(
                    success=True,
                    output_text=output,
                    metadata={"worker": "ollama_desktop", "model": self.model_name, "mode": "cli"},
                )
            return DesktopWorkerTaskResult(
                success=False,
                error_message=f"Local Ollama service not running on http://127.0.0.1:11434 or CLI. Error: {e}",
            )
