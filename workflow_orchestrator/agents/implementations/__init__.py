"""Agent implementations — real coding agent adapters.

Contains concrete implementations of IAgent for Claude Code, Cursor,
Codex CLI, and GitHub Copilot. Each agent exposes a manifest,
capabilities, supported transports, requirements, and health checks.
"""

from __future__ import annotations

from workflow_orchestrator.agents.implementations.claude_code_agent import ClaudeCodeAgent
from workflow_orchestrator.agents.implementations.cursor_agent import CursorAgent
from workflow_orchestrator.agents.implementations.codex_cli_agent import CodexCLIAgent
from workflow_orchestrator.agents.implementations.github_copilot_agent import GitHubCopilotAgent

__all__ = [
    "ClaudeCodeAgent",
    "CursorAgent",
    "CodexCLIAgent",
    "GitHubCopilotAgent",
]
