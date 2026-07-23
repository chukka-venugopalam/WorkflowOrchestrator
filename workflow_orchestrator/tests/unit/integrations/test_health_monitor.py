"""Tests for HealthMonitor integration module."""

from __future__ import annotations

from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from workflow_orchestrator.integrations.health_monitor import (
    HealthCheck,
    HealthMonitor,
    HealthReport,
    HealthStatus,
)


class TestHealthStatus:
    """Tests for HealthStatus enum."""

    def test_values(self) -> None:
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"


class TestHealthCheck:
    """Tests for HealthCheck data class."""

    def test_create(self) -> None:
        hc = HealthCheck(
            component_id="test",
            component_type="provider",
            status=HealthStatus.HEALTHY,
        )
        assert hc.component_id == "test"
        assert hc.is_healthy is True

    def test_unhealthy(self) -> None:
        hc = HealthCheck(
            component_id="test", component_type="provider",
            status=HealthStatus.UNHEALTHY, error="Connection failed",
        )
        assert hc.is_healthy is False
        assert hc.error == "Connection failed"

    def test_to_dict(self) -> None:
        hc = HealthCheck(
            component_id="test", component_type="cli",
            status=HealthStatus.HEALTHY, latency_ms=10.5,
        )
        d = hc.to_dict()
        assert d["component_id"] == "test"
        assert d["status"] == "healthy"
        assert d["latency_ms"] == 10.5


class TestHealthReport:
    """Tests for HealthReport data class."""

    def test_empty(self) -> None:
        report = HealthReport()
        assert report.total_checks == 0
        assert report.overall == HealthStatus.HEALTHY

    def test_with_checks(self) -> None:
        checks = [
            HealthCheck("a", "provider", HealthStatus.HEALTHY),
            HealthCheck("b", "provider", HealthStatus.DEGRADED),
        ]
        report = HealthReport(checks=checks, degraded_count=1)
        assert report.total_checks == 2
        assert report.degraded_count == 1

    def test_unhealthy_count(self) -> None:
        checks = [
            HealthCheck("a", "provider", HealthStatus.UNHEALTHY, error="err"),
            HealthCheck("b", "provider", HealthStatus.HEALTHY),
        ]
        report = HealthReport(checks=checks, unhealthy_count=1)
        assert report.unhealthy_count == 1

    def test_to_dict(self) -> None:
        report = HealthReport(checks=[], generated_at=None)
        d = report.to_dict()
        assert d["overall"] == "healthy"
        assert d["total_latency_ms"] == 0.0


class TestHealthMonitor:
    """Tests for HealthMonitor class."""

    def test_initial_state(self) -> None:
        event_bus = MagicMock()
        monitor = HealthMonitor(event_bus=event_bus)
        assert monitor.is_monitoring is False

    def test_register_checker(self) -> None:
        event_bus = MagicMock()
        monitor = HealthMonitor(event_bus=event_bus)

        def checker() -> HealthCheck:
            return HealthCheck("test", "cli", HealthStatus.HEALTHY)

        monitor.register_checker("cli", checker)
        report = monitor.check_all()
        assert report.total_checks == 1
        assert report.healthy_count == 1

    def test_checker_throws_exception(self) -> None:
        event_bus = MagicMock()
        monitor = HealthMonitor(event_bus=event_bus)

        def broken_checker() -> HealthCheck:
            raise RuntimeError("Check failed")

        monitor.register_checker("provider", broken_checker)
        report = monitor.check_all()
        assert report.total_checks == 1
        assert report.healthy_count == 0

    def test_check_all_empty(self) -> None:
        event_bus = MagicMock()
        monitor = HealthMonitor(event_bus=event_bus)
        report = monitor.check_all()
        assert report.total_checks == 0
        assert report.overall == HealthStatus.UNKNOWN

    def test_check_all_healthy(self) -> None:
        event_bus = MagicMock()
        monitor = HealthMonitor(event_bus=event_bus)

        def healthy() -> HealthCheck:
            return HealthCheck("ok", "cli", HealthStatus.HEALTHY)

        monitor.register_checker("cli", healthy)
        report = monitor.check_all()
        assert report.overall == HealthStatus.HEALTHY

    def test_check_all_degraded(self) -> None:
        event_bus = MagicMock()
        monitor = HealthMonitor(event_bus=event_bus)

        monitor.register_checker("cli", lambda: HealthCheck("c1", "cli", HealthStatus.HEALTHY))
        monitor.register_checker("cli", lambda: HealthCheck("c2", "cli", HealthStatus.DEGRADED))

        report = monitor.check_all()
        assert report.overall == HealthStatus.DEGRADED

    def test_check_all_unhealthy(self) -> None:
        event_bus = MagicMock()
        monitor = HealthMonitor(event_bus=event_bus)

        monitor.register_checker("cli", lambda: HealthCheck("c1", "cli", HealthStatus.UNHEALTHY, error="err"))
        report = monitor.check_all()
        assert report.overall == HealthStatus.UNHEALTHY

    def test_get_last_check(self) -> None:
        event_bus = MagicMock()
        monitor = HealthMonitor(event_bus=event_bus)

        def checker() -> HealthCheck:
            return HealthCheck("my-comp", "cli", HealthStatus.HEALTHY)

        monitor.register_checker("cli", checker)
        monitor.check_all()
        result = monitor.get_last_check("my-comp")
        assert result is not None
        assert result.component_id == "my-comp"

    def test_get_last_check_nonexistent(self) -> None:
        event_bus = MagicMock()
        monitor = HealthMonitor(event_bus=event_bus)
        result = monitor.get_last_check("nonexistent")
        assert result is None

    def test_health_changed_event(self) -> None:
        event_bus = MagicMock()
        monitor = HealthMonitor(event_bus=event_bus)

        def checker() -> HealthCheck:
            return HealthCheck("test", "cli", HealthStatus.UNHEALTHY, error="err")

        monitor.register_checker("cli", checker)
        monitor.check_all()
        assert event_bus.publish.called
        # Check the event name
        call_args = event_bus.publish.call_args
        assert call_args[0][0] == "integration.health_changed"

    def test_check_environment(self) -> None:
        event_bus = MagicMock()
        monitor = HealthMonitor(event_bus=event_bus)
        report = monitor.check_environment()
        assert report.total_checks >= 1

    def test_get_last_report(self) -> None:
        event_bus = MagicMock()
        monitor = HealthMonitor(event_bus=event_bus)

        monitor.register_checker("cli", lambda: HealthCheck("t", "cli", HealthStatus.HEALTHY))
        report = monitor.check_all()
        last = monitor.get_last_report()
        assert last is not None
        assert last.total_checks == report.total_checks

    def test_register_checker_multiple(self) -> None:
        event_bus = MagicMock()
        monitor = HealthMonitor(event_bus=event_bus)

        monitor.register_checker("provider", lambda: HealthCheck("p1", "provider", HealthStatus.HEALTHY))
        monitor.register_checker("provider", lambda: HealthCheck("p2", "provider", HealthStatus.HEALTHY))
        monitor.register_checker("cli", lambda: HealthCheck("c1", "cli", HealthStatus.HEALTHY))

        report = monitor.check_all()
        assert report.total_checks == 3

    def test_unregister_checker(self) -> None:
        event_bus = MagicMock()
        monitor = HealthMonitor(event_bus=event_bus)

        def checker() -> HealthCheck:
            return HealthCheck("test", "cli", HealthStatus.HEALTHY)

        monitor.register_checker("cli", checker)
        monitor.unregister_checker("cli", checker)
        report = monitor.check_all()
        assert report.total_checks == 0

    def test_start_stop_monitoring(self) -> None:
        event_bus = MagicMock()
        monitor = HealthMonitor(event_bus=event_bus)
        assert monitor.is_monitoring is False
        monitor.start_monitoring()
        assert monitor.is_monitoring is True
        monitor.stop_monitoring()
        assert monitor.is_monitoring is False
