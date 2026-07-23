"""Browser automation transport — controls browsers using Playwright.

Supports page navigation, form filling, screenshot capture,
and JavaScript execution through browser automation.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from workflow_orchestrator.transports.browser_transport import BrowserTransport
from workflow_orchestrator.transports.transport import (
    TransportError,
    TransportRequest,
    TransportResponse,
)

logger = logging.getLogger(__name__)


class BrowserAutomationTransport(BrowserTransport):
    """Browser automation transport using Playwright.

    Supports:
    - Page navigation and interaction
    - Form filling and button clicking
    - Screenshot capture
    - JavaScript execution
    - Content extraction
    """

    def __init__(
        self,
        browser_type: str = "chromium",
        headless: bool = True,
    ) -> None:
        """Initialize the browser automation transport.

        Args:
            browser_type: Type of browser ("chromium", "firefox", "webkit").
            headless: Whether to run in headless mode.
        """
        self._browser_type = browser_type
        self._headless = headless
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None

    async def _ensure_browser(self) -> Any:
        """Ensure the browser is launched.

        Returns:
            The browser page instance.
        """
        if self._page is not None:
            return self._page

        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            browser_type = getattr(self._playwright, self._browser_type)
            self._browser = await browser_type.launch(headless=self._headless)
            self._context = await self._browser.new_context()
            self._page = await self._context.new_page()
            logger.debug("Browser automation started (%s, headless=%s)", self._browser_type, self._headless)
            return self._page
        except ImportError:
            logger.warning("playwright not installed. Browser transport will use simulated mode.")
            return None
        except Exception as exc:
            raise TransportError(
                message=f"Failed to launch browser: {exc}",
                transport_type="browser_automation",
                recoverable=True,
            ) from exc

    async def send(self, request: TransportRequest) -> TransportResponse:
        """Execute a browser action.

        Actions are specified in request.metadata["action"]:
        - "navigate": Navigate to URL (request.url)
        - "click": Click element (request.metadata["selector"])
        - "fill": Fill form field (request.metadata["selector"], request.body)
        - "screenshot": Take screenshot
        - "evaluate": Run JavaScript (request.body)
        - "extract": Extract page content

        Args:
            request: The transport request with action metadata.

        Returns:
            TransportResponse with action result.
        """
        start_time = time.time()
        page = await self._ensure_browser()

        if page is None:
            return TransportResponse(
                body=f"[Browser Simulation] {request.metadata.get('action', 'navigate')} to {request.url}",
                duration_ms=(time.time() - start_time) * 1000,
                success=True,
            )

        action = request.metadata.get("action", "navigate")

        try:
            if action == "navigate":
                await page.goto(request.url, wait_until="networkidle")
                content = await page.content()
                return TransportResponse(
                    body=content[:10000],
                    duration_ms=(time.time() - start_time) * 1000,
                    success=True,
                )
            elif action == "click":
                selector = request.metadata.get("selector", "")
                await page.click(selector)
                return TransportResponse(
                    body=f"Clicked: {selector}",
                    duration_ms=(time.time() - start_time) * 1000,
                    success=True,
                )
            elif action == "fill":
                selector = request.metadata.get("selector", "")
                await page.fill(selector, request.body)
                return TransportResponse(
                    body=f"Filled: {selector}",
                    duration_ms=(time.time() - start_time) * 1000,
                    success=True,
                )
            elif action == "screenshot":
                path = request.metadata.get("path", "screenshot.png")
                await page.screenshot(path=path)
                return TransportResponse(
                    body=f"Screenshot saved to {path}",
                    duration_ms=(time.time() - start_time) * 1000,
                    success=True,
                )
            elif action == "evaluate":
                result = await page.evaluate(request.body)
                return TransportResponse(
                    body=str(result),
                    duration_ms=(time.time() - start_time) * 1000,
                    success=True,
                )
            elif action == "extract":
                content = await page.content()
                title = await page.title()
                text = await page.evaluate("() => document.body.innerText")
                return TransportResponse(
                    body=f"Title: {title}\n\n{text[:10000]}",
                    duration_ms=(time.time() - start_time) * 1000,
                    success=True,
                )
            else:
                raise TransportError(
                    message=f"Unknown browser action: {action}",
                    transport_type="browser_automation",
                    recoverable=False,
                )
        except Exception as exc:
            raise TransportError(
                message=str(exc),
                transport_type="browser_automation",
                recoverable=True,
                retryable=True,
            ) from exc

    async def cancel(self, request_id: str) -> None:
        """Cancel a browser action.

        Args:
            request_id: The request identifier.
        """
        logger.debug("Cancel requested for browser action '%s'", request_id)

    async def health(self) -> bool:
        """Check if the browser transport is healthy.

        Returns:
            True if browser is available.
        """
        if self._page is not None:
            try:
                return await self._page.evaluate("true") is True
            except Exception:
                return False
        return False

    async def disconnect(self) -> None:
        """Close the browser and release resources."""
        if self._browser:
            await self._browser.close()
        if hasattr(self, "_playwright") and self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._context = None
        self._page = None
