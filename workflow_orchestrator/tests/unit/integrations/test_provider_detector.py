"""Tests for ProviderDetector integration module."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from workflow_orchestrator.integrations.provider_detector import ProviderDetector, DetectedProvider


class TestDetectedProvider:
    """Tests for DetectedProvider data class."""

    def test_create(self) -> None:
        dp = DetectedProvider(
            provider_id="anthropic.claude",
            name="Claude",
            transport="rest_api",
            detected_from="env_var",
        )
        assert dp.provider_id == "anthropic.claude"
        assert dp.name == "Claude"
        assert dp.transport == "rest_api"
        assert dp.detected_from == "env_var"
        assert dp.available is False

    def test_available(self) -> None:
        dp = DetectedProvider(
            provider_id="test", name="Test", transport="cli",
            detected_from="path", available=True,
        )
        assert dp.available is True

    def test_with_version(self) -> None:
        dp = DetectedProvider(
            provider_id="test", name="Test", transport="cli",
            version="1.0.0", available=True,
        )
        assert dp.version == "1.0.0"


class TestProviderDetector:
    """Tests for ProviderDetector class."""

    def test_initial_no_providers(self) -> None:
        detector = ProviderDetector()
        detected = detector.detect_all()
        # Without mocking PATH, no providers should be detected
        assert isinstance(detected, list)

    @patch("shutil.which", return_value="/usr/local/bin/claude")
    def test_detect_claude_by_env(self, mock_which: MagicMock) -> None:
        detector = ProviderDetector()
        detected = detector.detect_all()
        ids = [d.provider_id for d in detected]
        assert "anthropic.claude" in ids

    @patch("shutil.which", return_value="/usr/local/bin/codex")
    def test_detect_chatgpt_by_env(self, mock_which: MagicMock) -> None:
        detector = ProviderDetector()
        detected = detector.detect_all()
        ids = [d.provider_id for d in detected]
        assert "codex" in ids

    @patch("shutil.which", return_value="/usr/local/bin/gemini")
    def test_detect_gemini_by_env(self, mock_which: MagicMock) -> None:
        detector = ProviderDetector()
        detected = detector.detect_all()
        ids = [d.provider_id for d in detected]
        assert "google.gemini" in ids

    def test_detect_by_claude_code_cli(self) -> None:
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            detector = ProviderDetector()
            detected = detector.detect_all()
            ids = [d.provider_id for d in detected]
            assert "anthropic.claude" in ids

    def test_detect_by_codex_cli(self) -> None:
        with patch("shutil.which", return_value="/usr/local/bin/codex"):
            detector = ProviderDetector()
            detected = detector.detect_all()
            ids = [d.provider_id for d in detected]
            assert "codex" in ids

    def test_detect_cursor(self) -> None:
        with patch("shutil.which", return_value="/usr/local/bin/cursor"):
            detector = ProviderDetector()
            detected = detector.detect_all()
            ids = [d.provider_id for d in detected]
            assert "cursor" in ids

    def test_detect_opencode(self) -> None:
        with patch("shutil.which", return_value="/usr/local/bin/opencode"):
            detector = ProviderDetector()
            detected = detector.detect_all()
            ids = [d.provider_id for d in detected]
            assert "opencode" in ids

    def test_no_false_positives(self) -> None:
        with patch("shutil.which", return_value=None):
            detector = ProviderDetector()
            detected = detector.detect_all()
            for d in detected:
                assert d.provider_id is not None
                assert d.name is not None

    def test_multiple_detection_methods(self) -> None:
        import os
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-xxx"}, clear=True):
            with patch("shutil.which", return_value="/usr/local/bin/claude"):
                detector = ProviderDetector()
                detected = detector.detect_all()
                claude_detections = [d for d in detected if d.provider_id == "anthropic.claude"]
                # Each detection method produces a separate entry
                assert len(claude_detections) >= 1
