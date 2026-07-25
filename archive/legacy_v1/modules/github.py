"""Git and GitHub automation for the Workflow Orchestrator.

Provides functions for common Git operations: status, add, commit,
and push. All commands are executed in the configured project directory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config import config_manager
from modules.logger import logger
from modules.terminal import CommandResult, run_command


@dataclass
class GitState:
    """Represents the current state of the Git repository.

    Attributes:
        branch: Current branch name.
        has_changes: True if there are uncommitted changes.
        untracked_files: List of untracked files.
        modified_files: List of modified files.
        staged_files: List of staged files.
        ahead: Number of commits ahead of remote.
        behind: Number of commits behind remote.
    """

    branch: str = "unknown"
    has_changes: bool = False
    untracked_files: list[str] = field(default_factory=list)
    modified_files: list[str] = field(default_factory=list)
    staged_files: list[str] = field(default_factory=list)
    ahead: int = 0
    behind: int = 0


def _get_project_dir() -> Optional[Path]:
    """Get the configured project directory.

    Returns:
        Optional[Path]: The project directory path, or None if not set.
    """
    project_dir = config_manager.config.default_project_directory
    if not project_dir:
        logger.warning("Default project directory is not configured.")
        return None

    path = Path(project_dir).expanduser().resolve()
    if not path.exists():
        logger.warning("Project directory does not exist: %s", path)
        return None

    return path


def git_status() -> Optional[GitState]:
    """Get the current Git repository status.

    Returns:
        Optional[GitState]: Current Git state, or None if the
            project directory is not configured or is not a Git repo.
    """
    project_dir = _get_project_dir()
    if not project_dir:
        return None

    result = run_command("git status --porcelain", cwd=project_dir)
    if not result.success:
        logger.warning("Not a Git repository or Git is not installed.")
        return None

    state = GitState()

    # Parse branch name
    branch_result = run_command(
        "git rev-parse --abbrev-ref HEAD", cwd=project_dir
    )
    if branch_result.success:
        state.branch = branch_result.stdout.strip()

    # Parse git status --porcelain output
    lines = [line for line in result.stdout.split("\n") if line.strip()]
    for line in lines:
        status = line[:2]
        file_path = line[3:].strip()

        if status == "??":
            state.untracked_files.append(file_path)
        elif " " in status and status[0] != " ":
            state.staged_files.append(file_path)
        elif status[1] != " ":
            state.modified_files.append(file_path)

    state.has_changes = bool(
        state.untracked_files or state.modified_files or state.staged_files
    )

    # Check ahead/behind
    remote_result = run_command(
        "git rev-list --count --left-right @{upstream}...HEAD 2>/dev/null || echo 0 0",
        cwd=project_dir,
    )
    if remote_result.success and remote_result.stdout.strip():
        parts = remote_result.stdout.strip().split()
        if len(parts) == 2:
            try:
                state.behind = int(parts[0])
                state.ahead = int(parts[1])
            except ValueError:
                pass

    return state


def git_add(files: Optional[list[str]] = None) -> bool:
    """Stage files for commit.

    Args:
        files: List of file paths to stage. If None, stages all changes.

    Returns:
        bool: True if the command succeeded.
    """
    project_dir = _get_project_dir()
    if not project_dir:
        return False

    if files:
        cmd = "git add " + " ".join(f'"{f}"' for f in files)
    else:
        cmd = "git add -A"

    result = run_command(cmd, cwd=project_dir)
    if result.success:
        logger.info("Files staged successfully.")
    else:
        logger.error("Failed to stage files: %s", result.stderr)
    return result.success


def _generate_commit_message() -> str:
    """Generate a default commit message with a timestamp.

    Returns:
        str: A timestamped commit message.
    """
    from datetime import datetime
    return f"Workflow update {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


def git_commit(message: str = "") -> bool:
    """Commit staged changes with a message.

    If the message is empty, a default message with a timestamp is generated.

    Args:
        message: Commit message. If empty, a default is generated.

    Returns:
        bool: True if the commit was created successfully.
    """
    project_dir = _get_project_dir()
    if not project_dir:
        return False

    commit_msg = message if message else _generate_commit_message()

    result = run_command(f'git commit -m "{commit_msg}"', cwd=project_dir)
    if result.success:
        logger.info("Committed: %s", commit_msg)
    else:
        logger.warning("Nothing to commit or commit failed: %s", result.stderr)
    return result.success


def git_push(branch: Optional[str] = None) -> bool:
    """Push commits to the remote repository.

    Args:
        branch: Branch name to push. If None, pushes the current branch.

    Returns:
        bool: True if the push was successful.
    """
    project_dir = _get_project_dir()
    if not project_dir:
        return False

    if not branch:
        branch_result = run_command(
            "git rev-parse --abbrev-ref HEAD", cwd=project_dir
        )
        if branch_result.success:
            branch = branch_result.stdout.strip()
        else:
            branch = "main"

    result = run_command(f"git push origin {branch}", cwd=project_dir)
    if result.success:
        logger.info("Pushed to origin/%s successfully.", branch)
    else:
        logger.error("Failed to push to origin/%s: %s", branch, result.stderr)
    return result.success


def auto_commit_and_push(message: Optional[str] = None) -> bool:
    """Run the full Git workflow: status check, add, commit, and push.

    Args:
        message: Optional commit message. Generated automatically if empty.

    Returns:
        bool: True if all steps completed successfully.
    """
    state = git_status()
    if state is None:
        return False

    if not state.has_changes:
        logger.info("No changes to commit.")
        return True

    logger.info(
        "Changes detected: %d untracked, %d modified, %d staged",
        len(state.untracked_files),
        len(state.modified_files),
        len(state.staged_files),
    )

    if not git_add():
        return False

    if not git_commit(message or ""):
        return False

    if not git_push():
        return False

    logger.info("Git workflow completed successfully.")
    return True
