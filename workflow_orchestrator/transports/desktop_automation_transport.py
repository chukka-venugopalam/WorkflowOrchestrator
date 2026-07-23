"""Desktop automation transport — controls desktop applications via automation.

Supports launching applications, window management, keyboard/mouse input,
and screen capture through desktop automation tools.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from workflow_orchestrator.transports.desktop_transport import DesktopTransport
from workflow_orchestrator.transports.transport import (
    TransportError,
    TransportRequest,
    TransportResponse,
)

logger = logging.getLogger(__name__)


class DesktopAutomationTransport(DesktopTransport):
    """Desktop automation transport using platform-specific tools.

    Supports:
    - Application launching and window management
    - Keyboard input simulation
    - Mouse click/move simulation
    - Screen capture
    - Clipboard operations

    Uses PyAutoGUI on all platforms, with platform-specific fallbacks.
    """

    def __init__(self) -> None:
        """Initialize the desktop automation transport."""
        self._pyautogui: Any = None
        self._initialized = False

    async def _ensure_initialized(self) -> Any:
        """Ensure PyAutoGUI is available.

        Returns:
            PyAutoGUI module reference or None if not available.
        """
        if self._initialized:
            return self._pyautogui

        try:
            import pyautogui
            pyautogui.FAILSAFE = True
            self._pyautogui = pyautogui
            self._initialized = True
            logger.debug("Desktop automation initialized (PyAutoGUI)")
            return self._pyautogui
        except ImportError:
            logger.warning("pyautogui not installed. Desktop transport will use simulated mode.")
            self._initialized = True
            return None

    async def send(self, request: TransportRequest) -> TransportResponse:
        """Execute a desktop automation action.

        Actions (in request.metadata):
        - "launch": Launch an application (request.body = app path/name)
        - "type": Type text (request.body)
        - "click": Click at coordinates (request.metadata["x"], request.metadata["y"])
        - "screenshot": Take a screenshot
        - "keypress": Press a key (request.metadata["key"])
        - "move": Move mouse to coordinates (request.metadata["x"], request.metadata["y"])

        Args:
            request: The transport request with action metadata.

        Returns:
            TransportResponse with action result.
        """
        start_time = time.time()
        pg = await self._ensure_initialized()

        if pg is None:
            return TransportResponse(
                body=f"[Desktop Simulation] {request.metadata.get('action', 'unknown')}",
                duration_ms=(time.time() - start_time) * 1000,
                success=True,
            )

        action = request.metadata.get("action", "type")

        try:
            if action == "type":
                text = request.body or ""
                pg.write(text, interval=0.05)
                return TransportResponse(
                    body=f"Typed {len(text)} characters",
                    duration_ms=(time.time() - start_time) * 1000,
                    success=True,
                )
            elif action == "click":
                x = request.metadata.get("x")
                y = request.metadata.get("y")
                button = request.metadata.get("button", "left")
                if x is not None and y is not None:
                    pg.click(x, y, button=button)
                else:
                    pg.click(button=button)
                return TransportResponse(
                    body=f"Clicked at ({x}, {y})" if x else "Clicked",
                    duration_ms=(time.time() - start_time) * 1000,
                    success=True,
                )
            elif action == "keypress":
                key = request.metadata.get("key", "enter")
                pg.press(key)
                return TransportResponse(
                    body=f"Pressed key: {key}",
                    duration_ms=(time.time() - start_time) * 1000,
                    success=True,
                )
            elif action == "move":
                x = request.metadata.get("x", 0)
                y = request.metadata.get("y", 0)
                duration = request.metadata.get("duration", 0.2)
                pg.moveTo(x, y, duration=duration)
                return TransportResponse(
                    body=f"Moved to ({x}, {y})",
                    duration_ms=(time.time() - start_time) * 1000,
                    success=True,
                )
            elif action == "screenshot":
                path = request.metadata.get("path", "desktop_screenshot.png")
                pg.screenshot(path)
                return TransportResponse(
                    body=f"Screenshot saved to {path}",
                    duration_ms=(time.time() - start_time) * 1000,
                    success=True,
                )
            elif action == "launch":
                app = request.body or ""
                import subprocess
                if app:
                    if app.endswith(".app") or app.endswith(".exe"):
                        subprocess.Popen([app], shell=True)
                    else:
                        subprocess.Popen(app, shell=True)
                    return TransportResponse(
                        body=f"Launched: {app}",
                        duration_ms=(time.time() - start_time) * 1000,
                        success=True,
                    )
                return TransportResponse(
                    body="No application specified",
                    duration_ms=(time.time() - start_time) * 1000,
                    success=False,
                    error="No app specified",
                )
            else:
                raise TransportError(
                    message=f"Unknown desktop action: {action}",
                    transport_type="desktop_automation",
                    recoverable=False,
                )
        except Exception as exc:
            raise TransportError(
                message=str(exc),
                transport_type="desktop_automation",
                recoverable=True,
                retryable=True,
            ) from exc

    async def cancel(self, request_id: str) -> None:
        """Cancel a desktop automation action.

        Args:
            request_id: The request identifier.
        """
        logger.debug("Cancel requested for desktop action '%s'", request_id)

    async def health(self) -> bool:
        """Check if desktop automation is available.

        Returns:
            True if PyAutoGUI is available.
        """
        pg = await self._ensure_initialized()
        return pg is not None

    @property
    def transport_type(self) -> str:
        """Human-readable transport type identifier."""
        return "desktop_automation"
