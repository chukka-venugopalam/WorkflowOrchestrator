"""Tests for EnvironmentDetector integration module."""

from __future__ import annotations

from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from workflow_orchestrator.integrations.environment_detector import EnvironmentDetector, EnvironmentInfo


class TestEnvironmentInfo:
    """Tests for EnvironmentInfo data class."""

    def test_create(self) -> None:
        info = EnvironmentInfo(
            os_name="Linux",
            cpu_count=8,
            ram_gb=16.0,
        )
        assert info.os_name == "Linux"
        assert info.cpu_count == 8
        assert info.ram_gb == 16.0

    def test_defaults(self) -> None:
        info = EnvironmentInfo()
        assert info.os_name == ""
        assert info.python_version == ""
        assert info.docker_available is False


class TestEnvironmentDetector:
    """Tests for EnvironmentDetector class."""

    def test_detect_returns_environment_info(self) -> None:
        detector = EnvironmentDetector()
        info = detector.detect()
        assert isinstance(info, EnvironmentInfo)

    def test_detect_os(self) -> None:
        detector = EnvironmentDetector()
        info = detector.detect()
        assert isinstance(info.os_name, str)
        assert len(info.os_name) > 0

    def test_detect_cpu_count(self) -> None:
        detector = EnvironmentDetector()
        info = detector.detect()
        assert isinstance(info.cpu_count, int)
        assert info.cpu_count > 0

    def test_detect_python(self) -> None:
        detector = EnvironmentDetector()
        info = detector.detect()
        assert isinstance(info.python_version, str)

    def test_detect_git(self) -> None:
        detector = EnvironmentDetector()
        info = detector.detect()
        assert isinstance(info.git_available, bool)

    def test_detect_docker(self) -> None:
        detector = EnvironmentDetector()
        info = detector.detect()
        assert isinstance(info.docker_available, bool)

    def test_detect_node(self) -> None:
        detector = EnvironmentDetector()
        info = detector.detect()
        assert isinstance(info.node_version, str)
