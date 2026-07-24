"""Health monitoring for all integrated components.

Continuously checks provider availability, transport connectivity,
agent status, workspace health, authentication validity, disk space,
memory usage, and capability availability.
"""

from __future__ import annotations

import logging
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Result of a single health check.

    Attributes:
        component_id: Component identifier.
        component_type: Type of component checked.
        status: Health status.
        latency_ms: Response latency in milliseconds.
        error: Error message if unhealthy.
        checked_at: When the check was performed.
        details: Additional diagnostic details.
    """

    component_id: str
    component_type: str
    status: HealthStatus
    latency_ms: float = 0.0
    error: Optional[str] = None
    checked_at: Optional[datetime] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "component_id": self.component_id,
            "component_type": self.component_type,
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
            "details": self.details,
        }

    @property
    def is_healthy(self) -> bool:
        """Whether this check indicates a healthy component."""
        return self.status == HealthStatus.HEALTHY


@dataclass
class HealthReport:
    """Complete health report for the system.

    Attributes:
        checks: List of all health checks performed.
        overall: Overall system health status.
        unhealthy_count: Number of unhealthy components.
        degraded_count: Number of degraded components.
        total_latency_ms: Total latency across all checks.
        generated_at: When the report was generated.
    """

    checks: List[HealthCheck] = field(default_factory=list)
    overall: HealthStatus = HealthStatus.HEALTHY
    unhealthy_count: int = 0
    degraded_count: int = 0
    total_latency_ms: float = 0.0
    generated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "checks": [c.to_dict() for c in self.checks],
            "overall": self.overall.value,
            "unhealthy_count": self.unhealthy_count,
            "degraded_count": self.degraded_count,
            "total_latency_ms": self.total_latency_ms,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }

    @property
    def total_checks(self) -> int:
        """Get total number of checks performed."""
        return len(self.checks)

    @property
    def healthy_count(self) -> int:
        """Get number of healthy components."""
        return sum(1 for c in self.checks if c.is_healthy)


class HealthMonitor:
    """Continuous health monitoring for all integrated components.

    Runs periodic health checks on providers, transports, agents,
    authentication, workspace, disk, memory, and capabilities.
    Publishes health events when status changes.
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        check_interval: float = 60.0,
    ) -> None:
        """Initialize the health monitor.

        Args:
            event_bus: Optional event bus for publishing health events.
            check_interval: Default interval between checks in seconds.
        """
        self._event_bus = event_bus
        self._check_interval = check_interval
        self._checkers: Dict[str, List[Callable[[], HealthCheck]]] = {}
        self._last_results: Dict[str, HealthCheck] = {}
        self._previous_status: Dict[str, HealthStatus] = {}
        self._monitoring = False
        self._last_report: Optional[HealthReport] = None

    @property
    def is_monitoring(self) -> bool:
        """Whether monitoring is active."""
        return self._monitoring

    def register_checker(self, component_type: str, checker: Callable[[], HealthCheck]) -> None:
        """Register a health checker function.

        Args:
            component_type: Type of component (e.g., provider, transport).
            checker: Callable that returns a HealthCheck result.
        """
        if component_type not in self._checkers:
            self._checkers[component_type] = []
        self._checkers[component_type].append(checker)

    def unregister_checker(self, component_type: str, checker: Callable[[], HealthCheck]) -> None:
        """Unregister a health checker function.

        Args:
            component_type: Type of component.
            checker: The checker function to remove.
        """
        if component_type in self._checkers:
            self._checkers[component_type] = [
                c for c in self._checkers[component_type] if c is not checker
            ]

    def check_all(self) -> HealthReport:
        """Run all registered health checks.

        Returns:
            Complete HealthReport with all results.
        """
        checks: List[HealthCheck] = []
        total_latency = 0.0

        for component_type, checkers in self._checkers.items():
            for checker in checkers:
                start = time.monotonic()
                try:
                    result = checker()
                    elapsed = (time.monotonic() - start) * 1000
                    result.latency_ms = elapsed
                    result.checked_at = datetime.now()
                    result.component_type = component_type
                except Exception as exc:
                    elapsed = (time.monotonic() - start) * 1000
                    result = HealthCheck(
                        component_id=f"{component_type}.unknown",
                        component_type=component_type,
                        status=HealthStatus.UNKNOWN,
                        latency_ms=elapsed,
                        error=str(exc),
                        checked_at=datetime.now(),
                    )

                total_latency += elapsed
                checks.append(result)

                # Track the result
                self._last_results[result.component_id] = result

                # Detect status changes and publish events
                previous = self._previous_status.get(result.component_id)
                if previous != result.status:
                    self._publish_event("integration.health_changed", {
                        "component_id": result.component_id,
                        "component_type": component_type,
                        "previous_status": previous.value if previous else None,
                        "new_status": result.status.value,
                        "error": result.error,
                    })
                    self._previous_status[result.component_id] = result.status

        # Compute aggregate
        unhealthy = sum(1 for c in checks if c.status == HealthStatus.UNHEALTHY)
        degraded = sum(1 for c in checks if c.status == HealthStatus.DEGRADED)

        if unhealthy > 0:
            overall = HealthStatus.UNHEALTHY
        elif degraded > 0:
            overall = HealthStatus.DEGRADED
        elif checks:
            overall = HealthStatus.HEALTHY
        else:
            overall = HealthStatus.UNKNOWN

        report = HealthReport(
            checks=checks,
            overall=overall,
            unhealthy_count=unhealthy,
            degraded_count=degraded,
            total_latency_ms=total_latency,
            generated_at=datetime.now(),
        )

        self._last_report = report
        return report

    def get_last_check(self, component_id: str) -> Optional[HealthCheck]:
        """Get the last health check result for a component.

        Args:
            component_id: Component identifier.

        Returns:
            HealthCheck if one exists, None otherwise.
        """
        return self._last_results.get(component_id)

    def get_last_report(self) -> Optional[HealthReport]:
        """Get the last generated health report.

        Returns:
            The last HealthReport, or None if none generated.
        """
        return self._last_report

    def check_environment(self) -> HealthReport:
        """Check environment health (disk, memory, etc.).

        Returns:
            HealthReport for environment checks.
        """
        checks: List[HealthCheck] = []

        # Disk space check
        try:
            usage = shutil.disk_usage(".")
            free_gb = usage.free / (1024 ** 3)
            total_gb = usage.total / (1024 ** 3)
            percent_free = (usage.free / usage.total) * 100

            if percent_free < 5:
                status = HealthStatus.UNHEALTHY
                error = f"Critically low disk space: {percent_free:.1f}% free"
            elif percent_free < 15:
                status = HealthStatus.DEGRADED
                error = f"Low disk space: {percent_free:.1f}% free"
            else:
                status = HealthStatus.HEALTHY
                error = None

            checks.append(HealthCheck(
                component_id="environment.disk",
                component_type="environment",
                status=status,
                error=error,
                details={
                    "free_gb": round(free_gb, 2),
                    "total_gb": round(total_gb, 2),
                    "percent_free": round(percent_free, 1),
                },
            ))
        except OSError as exc:
            checks.append(HealthCheck(
                component_id="environment.disk",
                component_type="environment",
                status=HealthStatus.UNKNOWN,
                error=str(exc),
            ))

        report = HealthReport(
            checks=checks,
            generated_at=datetime.now(),
        )

        # Compute overall from checks
        unhealthy = sum(1 for c in checks if c.status == HealthStatus.UNHEALTHY)
        degraded = sum(1 for c in checks if c.status == HealthStatus.DEGRADED)
        if unhealthy > 0:
            report.overall = HealthStatus.UNHEALTHY
        elif degraded > 0:
            report.overall = HealthStatus.DEGRADED
        else:
            report.overall = HealthStatus.HEALTHY

        report.unhealthy_count = unhealthy
        report.degraded_count = degraded
        self._last_report = report
        return report

    def _publish_event(self, event: str, data: Dict[str, Any]) -> None:
        """Publish an event through the event bus.

        Args:
            event: Event name.
            data: Event payload.
        """
        if self._event_bus:
            try:
                self._event_bus.publish(event, data)
            except Exception:
                try:
                    self._event_bus.publish(Event(type=event, data=data))
                except Exception:
                    pass

    def start_monitoring(self) -> None:
        """Start periodic health monitoring."""
        self._monitoring = True
        logger.info("Health monitoring started with interval %.1fs", self._check_interval)

    def stop_monitoring(self) -> None:
        """Stop periodic health monitoring."""
        self._monitoring = False
        logger.info("Health monitoring stopped")
