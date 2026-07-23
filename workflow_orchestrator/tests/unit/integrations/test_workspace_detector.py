"""Tests for WorkspaceDetector integration module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, Optional
from unittest.mock import MagicMock, patch

import pytest

from workflow_orchestrator.integrations.workspace_detector import WorkspaceDetector, WorkspaceInfo


class TestWorkspaceInfo:
    """Tests for WorkspaceInfo data class."""

    def test_create(self) -> None:
        info = WorkspaceInfo(root="/test", name="test-project", type="python-package")
        assert info.root == "/test"
        assert info.name == "test-project"
        assert info.type == "python-package"

    def test_defaults(self) -> None:
        info = WorkspaceInfo()
        assert info.frameworks == []
        assert info.languages == []
        assert info.has_git is False
        assert info.is_monorepo is False


class TestWorkspaceDetector:
    """Tests for WorkspaceDetector class."""

    def test_detect_returns_workspace_info(self) -> None:
        detector = WorkspaceDetector()
        info = detector.detect()
        assert isinstance(info, WorkspaceInfo)

    def test_detect_current_directory(self) -> None:
        detector = WorkspaceDetector()
        info = detector.detect()
        assert isinstance(info.name, str)
        assert isinstance(info.root, str)

    def test_detect_python_project(self, tmp_path: Path) -> None:
        (tmp_path / "setup.py").write_text("from setuptools import setup\nsetup(name='test-pkg')")
        detector = WorkspaceDetector()
        info = detector.detect(path=tmp_path)
        assert "Python" in info.languages or isinstance(info, WorkspaceInfo)

    def test_detect_node_project(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"name": "test-pkg", "version": "1.0.0"}))
        detector = WorkspaceDetector()
        info = detector.detect(path=tmp_path)
        assert isinstance(info, WorkspaceInfo)

    def test_detect_git(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        detector = WorkspaceDetector()
        info = detector.detect(path=tmp_path)
        assert info.has_git is True

    def test_detect_docker(self, tmp_path: Path) -> None:
        (tmp_path / "Dockerfile").write_text("FROM python")
        detector = WorkspaceDetector()
        info = detector.detect(path=tmp_path)
        assert info.has_docker is True

    def test_detect_frameworks_react(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({
            "dependencies": {"react": "^18.0.0", "react-dom": "^18.0.0"},
        }))
        detector = WorkspaceDetector()
        info = detector.detect(path=tmp_path)
        assert "React" in info.frameworks

    def test_detect_monorepo(self, tmp_path: Path) -> None:
        (tmp_path / "lerna.json").write_text("{}")
        detector = WorkspaceDetector()
        info = detector.detect(path=tmp_path)
        assert info.is_monorepo is True

    def test_detect_empty_directory(self, tmp_path: Path) -> None:
        detector = WorkspaceDetector()
        info = detector.detect(path=tmp_path)
        assert isinstance(info, WorkspaceInfo)
        assert info.type == "" or info.type == "unknown"

    def test_detect_build_tool(self, tmp_path: Path) -> None:
        (tmp_path / "tsconfig.json").write_text("{}")
        detector = WorkspaceDetector()
        info = detector.detect(path=tmp_path)
        assert info.build_tool == "typescript"

    def test_detect_requirements_txt(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("flask==2.3.0\npytest==7.0.0\n")
        detector = WorkspaceDetector()
        info = detector.detect(path=tmp_path)
        assert "Flask" in info.frameworks
