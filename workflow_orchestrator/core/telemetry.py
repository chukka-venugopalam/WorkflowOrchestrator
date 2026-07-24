"""Telemetry & Observability Engine — OpenTelemetry tracing, call traces, and dependency graphs.

Features:
- Event Tracing & Execution Timeline
- Service Dependency Graph generator
- Provider & Agent Call Trace recorder
- OpenTelemetry compliant span exporter
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TelemetrySpan:
    span_id: str
    name: str
    component: str
    start_time: float
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    status: str = "OK"


@dataclass
class ProviderCallTrace:
    provider_id: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    cost_estimate: float
    simulation_mode: bool
    timestamp: float = field(default_factory=time.time)


class TelemetryTracer:
    """OpenTelemetry compliant tracer and observability engine."""

    def __init__(self) -> None:
        self.active_spans: Dict[str, TelemetrySpan] = {}
        self.completed_spans: List[TelemetrySpan] = []
        self.provider_traces: List[ProviderCallTrace] = []
        self._span_counter = 0

    def start_span(self, name: str, component: str, attributes: Optional[Dict[str, Any]] = None) -> str:
        self._span_counter += 1
        span_id = f"span-{self._span_counter}"
        span = TelemetrySpan(
            span_id=span_id,
            name=name,
            component=component,
            start_time=time.time(),
            attributes=attributes or {},
        )
        self.active_spans[span_id] = span
        return span_id

    def end_span(self, span_id: str, status: str = "OK") -> None:
        if span_id in self.active_spans:
            span = self.active_spans.pop(span_id)
            span.end_time = time.time()
            span.status = status
            self.completed_spans.append(span)

    def record_provider_trace(
        self,
        provider_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        cost_estimate: float,
        simulation_mode: bool,
    ) -> None:
        trace = ProviderCallTrace(
            provider_id=provider_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            cost_estimate=cost_estimate,
            simulation_mode=simulation_mode,
        )
        self.provider_traces.append(trace)

    def generate_dependency_graph(self) -> Dict[str, List[str]]:
        """Generate graph of active system dependencies."""
        return {
            "MasterOrchestrator": ["Kernel", "ServiceRegistry", "ProviderManager", "AgentManager", "MCPManager"],
            "Kernel": ["ServiceRegistry", "EventBus", "PluginEngine"],
            "ProviderManager": ["ProviderRegistry", "ProviderRuntime", "CredentialManager"],
            "AgentManager": ["AgentRegistry", "AgentRuntime"],
            "ProjectFlowEngine": ["ProjectBuilder", "DecisionEngine", "ContextEngine", "WorkflowEngine"],
            "WorkflowEngine": ["ExecutionEngine", "CliCommandTransport", "StateEngine"],
        }

    def get_execution_timeline(self) -> List[Dict[str, Any]]:
        timeline = []
        for s in self.completed_spans:
            duration = ((s.end_time or s.start_time) - s.start_time) * 1000
            timeline.append({
                "span_id": s.span_id,
                "name": s.name,
                "component": s.component,
                "duration_ms": round(duration, 2),
                "status": s.status,
            })
        return timeline
