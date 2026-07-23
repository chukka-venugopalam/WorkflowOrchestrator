"""Tests for DependencyDetector integration module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, Optional
from unittest.mock import MagicMock, patch

import pytest

from workflow_orchestrator.integrations.dependency_detector import DependencyDetector, DependencyInfo


class TestDependencyInfo:
    """Tests for DependencyInfo data class."""

    def test_create(self) -> None:
        info = DependencyInfo(
            languages=["Python", "JavaScript/TypeScript"],
            total_dependencies=10,
        )
        assert "Python" in info.languages
        assert info.total_dependencies == 10

    def test_defaults(self) -> None:
        info = DependencyInfo()
        assert info.languages == []
        assert info.frameworks == []
        assert info.total_dependencies == 0


class TestDependencyDetector:
    """Tests for DependencyDetector class."""

    def test_detect_returns_dependency_info(self) -> None:
        detector = DependencyDetector()
        info = detector.detect()
        assert isinstance(info, DependencyInfo)

    def test_detect_python_deps(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("flask==2.3.0\nrequests==2.31.0\npsycopg2==2.9.0\n")
        detector = DependencyDetector()
        info = detector.detect(path=tmp_path)
        assert "Python" in info.languages
        assert info.total_dependencies >= 3

    def test_detect_node_deps(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({
            "dependencies": {"react": "^18.0.0", "next": "^14.0.0"},
            "devDependencies": {"jest": "^29.0.0"},
        }))
        detector = DependencyDetector()
        info = detector.detect(path=tmp_path)
        assert "JavaScript/TypeScript" in info.languages
        assert info.total_dependencies >= 2

    def test_detect_go_deps(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text("module example.com/app\ngo 1.21\n")
        detector = DependencyDetector()
        info = detector.detect(path=tmp_path)
        assert "Go" in info.languages

    def test_detect_rust_deps(self, tmp_path: Path) -> None:
        (tmp_path / "Cargo.toml").write_text("[dependencies]\nserde = \"1.0\"\ntokio = \"1.0\"\n")
        detector = DependencyDetector()
        info = detector.detect(path=tmp_path)
        assert "Rust" in info.languages

    def test_detect_empty_dir(self, tmp_path: Path) -> None:
        detector = DependencyDetector()
        info = detector.detect(path=tmp_path)
        assert info.total_dependencies == 0

    def test_detect_databases(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({
            "dependencies": {"mongoose": "^7.0.0", "redis": "^4.0.0"},
        }))
        detector = DependencyDetector()
        info = detector.detect(path=tmp_path)
        assert "MongoDB" in info.databases
        assert "Redis" in info.databases

    def test_detect_cicd(self, tmp_path: Path) -> None:
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        detector = DependencyDetector()
        info = detector.detect(path=tmp_path)
        assert "GitHub Actions" in info.ci_cd

    def test_detect_build_tools(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({
            "dependencies": {},
            "devDependencies": {"vite": "^5.0.0", "typescript": "^5.0.0"},
        }))
        detector = DependencyDetector()
        info = detector.detect(path=tmp_path)
        assert "Vite" in info.build_tools or "Typescript" in info.build_tools
