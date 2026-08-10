"""Desktop Browser Transport — Optional Playwright Web AI Driver.

Provides optional web portal automation for ChatGPT Web, Gemini Web, and Claude Web.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class DesktopBrowserTransport:
    """Optional web AI automation driver using Playwright."""

    def __init__(self, portal_name: str = "chatgpt") -> None:
        self.portal_name = portal_name
        self.is_connected = False

    def is_available(self) -> bool:
        """Check if Playwright browser automation is available."""
        try:
            import playwright
            return True
        except ImportError:
            return False

    def start_session(self) -> bool:
        """Initialize optional browser session."""
        if not self.is_available():
            logger.info(f"Playwright not installed; optional browser worker '{self.portal_name}' operating in offline mode.")
            return False
        self.is_connected = True
        return True

    def send_prompt(self, prompt: str, timeout_seconds: float = 60.0) -> str:
        """Dispatch prompt to web portal DOM input via Playwright with persistent context."""
        if not self.is_available():
            raise RuntimeError(f"Playwright browser transport not installed for '{self.portal_name}'")

        import time
        from pathlib import Path
        from playwright.sync_api import sync_playwright

        user_data_dir = Path.home() / ".config" / "workflow_orchestrator" / "browser_profile"
        user_data_dir.mkdir(parents=True, exist_ok=True)

        url_map = {
            "google.gemini": "https://gemini.google.com/app",
            "gemini": "https://gemini.google.com/app",
            "openai.chatgpt": "https://chatgpt.com",
            "chatgpt": "https://chatgpt.com",
            "anthropic.claude": "https://claude.ai/chats",
            "claude": "https://claude.ai/chats",
        }
        target_url = url_map.get(self.portal_name.lower(), "https://gemini.google.com/app")

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            page = context.new_page()
            try:
                page.goto(target_url, wait_until="commit", timeout=25000)
                page.wait_for_load_state("domcontentloaded", timeout=15000)

                # Find input textarea / contenteditable div
                input_selector = (
                    "rich-textarea p, textarea, div[contenteditable='true'], "
                    "div[role='textbox'], p.placeholder, #prompt-textarea"
                )
                page.wait_for_selector(input_selector, timeout=10000)
                input_elem = page.locator(input_selector).first
                input_elem.click()
                input_elem.fill(prompt)

                # Press Enter or click send button
                send_button_selector = "button[aria-label*='Send'], button[aria-label*='Submit'], button.send-button"
                if page.locator(send_button_selector).count() > 0:
                    page.locator(send_button_selector).first.click()
                else:
                    page.keyboard.press("Enter")

                # Wait for response text element to populate & stabilize
                response_selector = (
                    "message-content, .model-response-text, div.markdown, "
                    "div[data-message-author-role='assistant'], .prose"
                )
                page.wait_for_selector(response_selector, timeout=int(timeout_seconds * 1000))
                time.sleep(2.0)  # Allow response completion

                responses = page.locator(response_selector).all()
                if responses:
                    last_resp = responses[-1].inner_text()
                    if last_resp and last_resp.strip():
                        logger.info("Captured real web AI browser response (%d bytes) from %s", len(last_resp), self.portal_name)
                        return last_resp.strip()

                raise RuntimeError(f"Web AI portal '{self.portal_name}' returned empty response text")
            except Exception as err:
                logger.warning("Browser transport '%s' navigation failed: %s", self.portal_name, err)
                raise RuntimeError(f"Browser transport '{self.portal_name}' failed: {err}") from err
            finally:
                context.close()

    def stop_session(self) -> None:
        """Close browser session."""
        self.is_connected = False
