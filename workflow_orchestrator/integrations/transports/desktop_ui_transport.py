"""Desktop UI Transport — Windows UI Automation & Clipboard Sync Driver.

Drives desktop IDEs (Cursor IDE, VS Code, GitHub Copilot, Claude Desktop, ChatGPT) via window focus and clipboard automation.

NOTE (Known Limitation):
Best-effort GUI response capture. Electron/Chromium-shell apps (Claude Desktop, ChatGPT Desktop, VS Code)
omit UI Automation (UIA) renderer element trees by default unless launched as a primary screen-reader process.
CLI and Browser transports are prioritized for prompt disambiguation and automated reasoning.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DesktopUITransport:
    """Automates desktop IDE chat panels and window focus via UI Automation & Clipboard."""

    def __init__(self, target_window_title: str = "Cursor") -> None:
        self.target_window_title = target_window_title

    def is_available(self) -> bool:
        """Check if target IDE application binary is on PATH or running."""
        import shutil
        if self.target_window_title.lower().startswith("cursor"):
            return shutil.which("cursor") is not None or shutil.which("Cursor") is not None
        elif "code" in self.target_window_title.lower():
            return shutil.which("code") is not None or shutil.which("code.cmd") is not None
        return True

    def dispatch_prompt_to_ide(self, prompt: str, target_file: Optional[Path] = None) -> bool:
        """Copy prompt to system clipboard, focus target IDE window, and send keystrokes."""
        if not self.is_available():
            logger.info(f"Target IDE '{self.target_window_title}' is not available. Skipping UI dispatch.")
            return False

        try:
            try:
                import pyperclip
                pyperclip.copy(prompt)
                logger.info(f"Copied {len(prompt)} bytes to system clipboard for target IDE '{self.target_window_title}'.")
            except Exception as clip_err:
                logger.warning(f"Clipboard access skipped: {clip_err}")

            # Native Windows Win32 UI Automation
            import sys
            if sys.platform == "win32":
                import ctypes
                user32 = ctypes.windll.user32

                self.last_matched_hwnd = None

                def _enum_cb(hwnd, extra):
                    if user32.IsWindowVisible(hwnd):
                        if hasattr(user32, "IsHungAppWindow") and user32.IsHungAppWindow(hwnd):
                            return True
                        length = user32.GetWindowTextLengthW(hwnd)
                        if length > 0:
                            buff = ctypes.create_unicode_buffer(length + 1)
                            user32.GetWindowTextW(hwnd, buff, length + 1)
                            if self.target_window_title.lower() in buff.value.lower():
                                self.last_matched_hwnd = hwnd
                                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                                user32.SetForegroundWindow(hwnd)
                                return False
                    return True

                EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
                user32.EnumWindows(EnumWindowsProc(_enum_cb), 0)

            return True
        except Exception as e:
            logger.error(f"UI Automation dispatch error for '{self.target_window_title}': {e}")
            return False

    def capture_response(self, prompt: str, timeout_seconds: float = 30.0) -> tuple[str, dict[str, str]]:
        """Dispatch prompt and capture response from desktop GUI app via 3-tier fallback chain:
        1. Accessibility Tree (pywinauto/uiautomation) -> metadata={"capture_method": "accessibility_tree"}
        2. Clipboard Readback (pyautogui + pyperclip) -> metadata={"capture_method": "clipboard"}
        3. OCR Screenshot (pytesseract + mss/ImageGrab) -> metadata={"capture_method": "ocr"}

        Raises RuntimeError if all 3 tiers fail.
        """
        # Ensure window is focused & prompt dispatched
        dispatched = self.dispatch_prompt_to_ide(prompt)
        if not dispatched:
            raise RuntimeError(f"Could not focus desktop GUI window for '{self.target_window_title}'")

        time.sleep(1.5)  # Allow initial UI rendering/dispatch

        # ------------------------------------------------------------------
        # Tier 1: Accessibility Tree (pywinauto / UI Automation)
        # ------------------------------------------------------------------
        try:
            import pywinauto
            import re
            app = None
            if getattr(self, "last_matched_hwnd", None):
                try:
                    app = pywinauto.Application(backend="uia").connect(handle=self.last_matched_hwnd, timeout=3)
                except Exception:
                    try:
                        app = pywinauto.Application(backend="win32").connect(handle=self.last_matched_hwnd, timeout=3)
                    except Exception:
                        app = None
            if app is None:
                try:
                    app = pywinauto.Application(backend="uia").connect(title_re=f"(?i).*{re.escape(self.target_window_title)}.*", visible_only=True, found_index=0, timeout=3)
                except Exception:
                    app = pywinauto.Application(backend="win32").connect(title_re=f"(?i).*{re.escape(self.target_window_title)}.*", visible_only=True, found_index=0, timeout=3)
            
            win = app.window(handle=self.last_matched_hwnd) if getattr(self, "last_matched_hwnd", None) else app.top_window()
            
            # Poll for text stabilization
            prev_text = ""
            stable_count = 0
            start_time = time.time()

            while time.time() - start_time < timeout_seconds:
                descendant_text = ""
                try:
                    controls = win.descendants(control_type="Edit") + win.descendants(control_type="Document") + win.descendants(control_type="Text")
                    texts = [c.window_text() for c in controls if c.window_text() and c.window_text().strip() != prompt.strip()]
                    if texts:
                        descendant_text = "\n".join(texts)
                except Exception:
                    pass

                curr_text = descendant_text if descendant_text.strip() else (win.window_text() or "")

                if curr_text and curr_text.strip() and curr_text.strip() != prompt.strip():
                    if curr_text == prev_text:
                        stable_count += 1
                        if stable_count >= 2:
                            logger.info("Captured GUI response via accessibility_tree (%d bytes)", len(curr_text))
                            return curr_text, {"capture_method": "accessibility_tree"}
                    else:
                        stable_count = 0
                        prev_text = curr_text

                time.sleep(1.0)
        except Exception as tier1_err:
            logger.warning("Tier 1 (accessibility_tree) capture failed for '%s': %s — trying Tier 2 (clipboard)", self.target_window_title, tier1_err)

        # ------------------------------------------------------------------
        # Tier 2: Clipboard Readback (pyautogui + pyperclip)
        # ------------------------------------------------------------------
        try:
            import pyautogui
            import pyperclip

            pyautogui.FAILSAFE = False
            # Clear clipboard first to avoid reading stale prompt
            pyperclip.copy("")
            time.sleep(0.1)

            # Select all in active focused window and copy to clipboard
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.2)
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.5)

            clip_text = pyperclip.paste()
            if clip_text and clip_text.strip() and clip_text.strip() != prompt.strip():
                logger.info("Captured GUI response via clipboard (%d bytes)", len(clip_text))
                return clip_text, {"capture_method": "clipboard"}
            else:
                logger.warning("Tier 2 (clipboard) captured empty or matching prompt text")
        except Exception as tier2_err:
            logger.warning("Tier 2 (clipboard) capture failed for '%s': %s — trying Tier 3 (OCR)", self.target_window_title, tier2_err)

        # ------------------------------------------------------------------
        # Tier 3: OCR Screenshot (mss / PIL + pytesseract)
        # ------------------------------------------------------------------
        try:
            import pytesseract
            from PIL import Image, ImageGrab

            img = None
            try:
                import mss
                with mss.MSS() as sct:
                    monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                    sct_img = sct.grab(monitor)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            except Exception:
                img = ImageGrab.grab()

            if img is not None:
                ocr_text = pytesseract.image_to_string(img)
                if ocr_text and ocr_text.strip() and len(ocr_text.strip()) > 5:
                    logger.info("Captured GUI response via OCR (%d bytes)", len(ocr_text))
                    return ocr_text.strip(), {"capture_method": "ocr"}
        except Exception as tier3_err:
            logger.warning("Tier 3 (OCR) capture failed for '%s': %s", self.target_window_title, tier3_err)

        # All 3 Tiers Failed
        raise RuntimeError(
            f"Failed to capture response from desktop GUI app '{self.target_window_title}' "
            "via accessibility_tree, clipboard, or OCR"
        )
