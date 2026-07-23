"""Provider metrics — tracks execution metrics for provider adapters.

Includes request counts, latency, error rates, token usage, and costs.
All metrics are provider-agnostic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderMetrics:
    """Tracks execution metrics for a provider adapter.

    Attributes:
        provider_id: The provider identifier.
        total_requests: Total number of execution requests.
        successful_requests: Number of successful requests.
        failed_requests: Number of failed requests.
        total_latency_ms: Cumulative latency in milliseconds.
        total_tokens_input: Cumulative input tokens.
        total_tokens_output: Cumulative output tokens.
        total_cost: Cumulative cost in abstract units.
        last_request_time: Timestamp of the last request.
        errors_by_type: Count of errors by error type.
    """

    provider_id: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_cost: float = 0.0
    last_request_time: float = 0.0
    errors_by_type: dict[str, int] = field(default_factory=dict)

    def record_success(self, latency_ms: float, tokens_input: int = 0, tokens_output: int = 0, cost: float = 0.0) -> None:
        """Record a successful request.

        Args:
            latency_ms: Request latency in milliseconds.
            tokens_input: Input tokens used.
            tokens_output: Output tokens generated.
            cost: Cost of the request.
        """
        self.total_requests += 1
        self.successful_requests += 1
        self.total_latency_ms += latency_ms
        self.total_tokens_input += tokens_input
        self.total_tokens_output += tokens_output
        self.total_cost += cost
        self.last_request_time = time.time()

    def record_failure(self, latency_ms: float, error_type: str = "unknown") -> None:
        """Record a failed request.

        Args:
            latency_ms: Request latency in milliseconds.
            error_type: Type of error that occurred.
        """
        self.total_requests += 1
        self.failed_requests += 1
        self.total_latency_ms += latency_ms
        self.last_request_time = time.time()
        self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1

    @property
    def error_rate(self) -> float:
        """Calculate the error rate (0.0 to 1.0).

        Returns:
            Error rate as a fraction.
        """
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    @property
    def average_latency_ms(self) -> float:
        """Calculate the average latency per request.

        Returns:
            Average latency in milliseconds.
        """
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary."""
        return {
            "provider_id": self.provider_id,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "error_rate": round(self.error_rate, 4),
            "average_latency_ms": round(self.average_latency_ms, 2),
            "total_latency_ms": round(self.total_latency_ms, 2),
            "total_tokens_input": self.total_tokens_input,
            "total_tokens_output": self.total_tokens_output,
            "total_cost": round(self.total_cost, 6),
            "last_request_time": self.last_request_time,
            "errors_by_type": dict(self.errors_by_type),
        }
