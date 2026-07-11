"""Prompt template management for the Workflow Orchestrator.

Stores and manages prompt templates used for generating
AI-assisted coding instructions. Templates are stored
as text files in the prompts/ directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from modules.logger import logger

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
TEMPLATE_FILE = PROMPTS_DIR / "template.txt"
EXAMPLES_DIR = PROMPTS_DIR / "examples"


def load_template(template_path: Optional[Path] = None) -> str:
    """Load a prompt template from a file.

    Args:
        template_path: Path to the template file. If None,
            loads the default template.

    Returns:
        str: The template content, or an empty string if the file
            does not exist or cannot be read.
    """
    path = template_path or TEMPLATE_FILE

    if not path.exists():
        logger.warning("Template file not found: %s", path)
        return ""

    try:
        content = path.read_text(encoding="utf-8")
        logger.info("Loaded template from %s", path)
        return content
    except OSError as exc:
        logger.error("Failed to read template file %s: %s", path, exc)
        return ""


def save_template(content: str, template_path: Optional[Path] = None) -> bool:
    """Save a prompt template to a file.

    Args:
        content: The template content to save.
        template_path: Path to save the template. If None,
            saves to the default template file.

    Returns:
        bool: True if the template was saved successfully.
    """
    path = template_path or TEMPLATE_FILE

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        logger.info("Saved template to %s", path)
        return True
    except OSError as exc:
        logger.error("Failed to save template to %s: %s", path, exc)
        return False


def list_templates() -> list[Path]:
    """List all template files in the prompts directory.

    Returns:
        list[Path]: Sorted list of template file paths.
    """
    if not PROMPTS_DIR.exists():
        logger.debug("Prompts directory does not exist: %s", PROMPTS_DIR)
        return []

    templates = sorted(PROMPTS_DIR.glob("*.txt"))
    logger.debug("Found %d template files.", len(templates))
    return templates


def list_examples() -> list[Path]:
    """List all example prompt files in the examples directory.

    Returns:
        list[Path]: Sorted list of example file paths.
    """
    if not EXAMPLES_DIR.exists():
        logger.debug("Examples directory does not exist: %s", EXAMPLES_DIR)
        return []

    examples = sorted(EXAMPLES_DIR.glob("*.txt"))
    logger.debug("Found %d example files.", len(examples))
    return examples


def format_prompt(template: str, **kwargs: str) -> str:
    """Format a prompt template by substituting placeholders.

    Placeholders in the template should use Python's str.format
    syntax, e.g., {task_description}.

    Args:
        template: The template string with placeholders.
        **kwargs: Key-value pairs for placeholder substitution.

    Returns:
        str: The formatted prompt with placeholders replaced.
    """
    try:
        formatted = template.format(**kwargs)
        return formatted
    except KeyError as exc:
        logger.warning("Missing template placeholder: %s", exc)
        return template
