"""Plugin system for the Workflow Orchestrator.

Each plugin wraps a specific capability (browser, terminal, VS Code, Git, etc.)
and exposes it through a common interface for the workflow engine.
"""

from workflow_orchestrator.plugins.registry import PluginRegistry
from workflow_orchestrator.plugins.base import Plugin, PluginMetadata

__all__ = [
    "Plugin",
    "PluginMetadata",
    "PluginRegistry",
]
