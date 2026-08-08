"""Optional Web Desktop Worker — optional Playwright browser driver for ChatGPT Web, Gemini Web, and Claude Web.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from workflow_orchestrator.workers.desktop_worker import (
    DesktopWorker,
    DesktopWorkerTaskResult,
)
from workflow_orchestrator.integrations.transports.desktop_browser_transport import DesktopBrowserTransport

logger = logging.getLogger(__name__)


class OptionalWebDesktopWorker(DesktopWorker):
    """Optional Desktop AI worker wrapping web AI portals via Playwright."""

    def __init__(self, portal_name: str = "chatgpt") -> None:
        super().__init__(
            worker_id=f"{portal_name}_web_desktop",
            name=f"{portal_name.capitalize()} Web Worker (Optional)",
            skills=["research", "specification", "documentation"],
            transport_type="browser",
        )
        self.portal_name = portal_name
        self.browser_transport = DesktopBrowserTransport(portal_name=portal_name)

    def discover(self) -> bool:
        return self.browser_transport.is_available()

    def _execute_desktop_task(self, task_payload: Dict[str, Any]) -> DesktopWorkerTaskResult:
        """Execute task via Playwright browser transport safely with full exception handling."""
        prompt = task_payload.get("prompt", "Execute research task")

        if not self.discover():
            err_msg = f"Playwright browser transport not available for optional web worker '{self.portal_name}'."
            logger.warning(err_msg)
            return DesktopWorkerTaskResult(
                success=False,
                output_text=err_msg,
                error_message=err_msg,
                generated_files=[],
                metadata={"worker": self.worker_id, "portal": self.portal_name, "reason": "playwright_not_installed"},
            )

        try:
            output = self.browser_transport.send_prompt(prompt)
            if not output or output.strip().startswith(("Error", "Failed", "[Error]")) or "not installed" in output.lower():
                err_text = output or "Browser transport returned empty or error output"
                return DesktopWorkerTaskResult(
                    success=False,
                    output_text=err_text,
                    error_message=err_text,
                    generated_files=[],
                    metadata={"worker": self.worker_id, "portal": self.portal_name, "error": "browser_error_response"},
                )

            return DesktopWorkerTaskResult(
                success=True,
                output_text=output,
                generated_files=[],
                metadata={"worker": self.worker_id, "portal": self.portal_name, "optional": True},
            )
        except Exception as exc:
            err_msg = f"Optional web worker '{self.portal_name}' execution exception: {exc}"
            logger.warning(err_msg)
            return DesktopWorkerTaskResult(
                success=False,
                output_text=err_msg,
                error_message=str(exc),
                generated_files=[],
                metadata={"worker": self.worker_id, "portal": self.portal_name, "error": str(exc)},
            )
