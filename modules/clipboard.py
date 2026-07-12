"""Clipboard operations for the Workflow Orchestrator.

Provides functions to copy text to and read text from
the system clipboard, using the pyperclip library.
"""

from __future__ import annotations

from typing import Optional

from modules.logger import logger

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False


def copy_to_clipboard(text: str) -> bool:
    """Copy text to the system clipboard.

    Args:
        text: The text string to copy to the clipboard.

    Returns:
        bool: True if the text was copied successfully, False otherwise.
    """
    if not HAS_PYPERCLIP:
        logger.error(
            "pyperclip is not installed. Install it with: pip install pyperclip"
        )
        return False

    if not text:
        logger.warning("Attempted to copy empty text to clipboard.")
        return False

    try:
        pyperclip.copy(text)
        preview = text[:50] + "..." if len(text) > 50 else text
        logger.info("Copied to clipboard: '%s'", preview)
        return True
    except pyperclip.PyperclipException as exc:
        logger.error("Failed to copy to clipboard: %s", exc)
        return False


def read_from_clipboard() -> Optional[str]:
    """Read text from the system clipboard.

    Returns:
        Optional[str]: The clipboard contents as a string,
            or None if reading failed.
    """
    if not HAS_PYPERCLIP:
        logger.error(
            "pyperclip is not installed. Install it with: pip install pyperclip"
        )
        return None

    try:
        text = pyperclip.paste()
        logger.info("Read %d characters from clipboard.", len(text))
        return text
    except pyperclip.PyperclipException as exc:
        logger.error("Failed to read from clipboard: %s", exc)
        return None
