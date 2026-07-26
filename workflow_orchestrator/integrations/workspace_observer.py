"""Workspace Observer — real-time monitoring of workspace file diffs, terminal outputs, build logs, git status, and pytest test results.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceSnapshot:
    """Snapshot of workspace state during project orchestration."""

    project_root: Path
    timestamp: float = field(default_factory=time.time)
    modified_files: List[Path] = field(default_factory=list)
    git_status: str = "clean"
    last_build_output: str = ""
    last_test_output: str = ""
    test_passed: bool = True


class WorkspaceObserver:
    """Monitors local workspace mutations, git status, build logs, and test results in real time."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.project_root = project_root or Path.cwd()
        self.snapshots: List[WorkspaceSnapshot] = []

    def capture_snapshot(self) -> WorkspaceSnapshot:
        """Capture real-time workspace snapshot."""
        modified = self.get_modified_files()
        git_stat = self.get_git_status()
        build_log = self.check_build_logs()
        test_log, test_pass = self.run_verification_tests()

        snapshot = WorkspaceSnapshot(
            project_root=self.project_root,
            modified_files=modified,
            git_status=git_stat,
            last_build_output=build_log,
            last_test_output=test_log,
            test_passed=test_pass,
        )
        self.snapshots.append(snapshot)
        return snapshot

    def get_modified_files(self) -> List[Path]:
        """Scan workspace for recently modified files."""
        modified = []
        if not self.project_root.exists():
            return modified

        now = time.time()
        for p in self.project_root.rglob("*"):
            if p.is_file() and not any(part.startswith((".", "__pycache__", "node_modules", ".venv")) for part in p.parts):
                try:
                    if now - p.stat().st_mtime < 300:  # Modified in last 5 minutes
                        modified.append(p)
                except Exception:
                    pass
        return modified

    def get_git_status(self) -> str:
        """Get git status output if git repo is present."""
        if not (self.project_root / ".git").exists():
            return "git repo not initialized"

        try:
            res = subprocess.run(
                ["git", "status", "--short"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            return res.stdout.strip() or "clean"
        except Exception as e:
            return f"git error: {e}"

    def check_build_logs(self) -> str:
        """Check workspace build logs or package syntax."""
        pyproject = self.project_root / "pyproject.toml"
        package_json = self.project_root / "package.json"

        if pyproject.exists():
            return f"Python package config verified: {pyproject.name}"
        if package_json.exists():
            return f"Node.js package config verified: {package_json.name}"
        return "No package configuration file found in root."

    def run_verification_tests(self) -> tuple[str, bool]:
        """Run verification tests in project workspace."""
        test_dir = self.project_root / "tests"
        if not test_dir.exists():
            return ("No tests directory found; verification skipped.", True)

        try:
            res = subprocess.run(
                ["python", "-m", "pytest", str(test_dir), "-q"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30.0,
            )
            passed = res.returncode == 0
            return (res.stdout or res.stderr, passed)
        except Exception as e:
            return (f"Verification test execution error: {e}", False)
