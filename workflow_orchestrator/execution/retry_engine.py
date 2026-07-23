"""Retry engine for handling step execution failures.

Supports:
- Retry policies (configurable per step)
- Exponential backoff
- Maximum retry limits
- Failure classification
- Abort policies
- Error type-aware retry decisions
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from workflow_orchestrator.models import StepResult, StepStatus

logger = logging.getLogger(__name__)


class ErrorClass(Enum):
    """Classification of execution errors."""

    TRANSIENT = "transient"
    TIMEOUT = "timeout"
    VERIFICATION_FAILURE = "verification_failure"
    CONTRACT_VIOLATION = "contract_violation"
    CAPABILITY_UNRESOLVED = "capability_unresolved"
    PLUGIN_ERROR = "plugin_error"
    UNKNOWN = "unknown"


class RetryDecision(Enum):
    """Decision after evaluating whether to retry."""

    RETRY = "retry"
    ABORT = "abort"
    ESCALATE = "escalate"
    SKIP = "skip"


@dataclass
class RetryPolicy:
    """Configuration for retrying a failed step.

    Attributes:
        max_retries: Maximum number of retry attempts.
        delay: Initial delay in seconds.
        backoff: Backoff multiplier (e.g., 2.0 = double delay each retry).
        max_delay: Maximum delay between retries.
        retryable_errors: Error classes that should be retried.
            If empty, all errors are retryable.
        abort_on: Error classes that should abort immediately.
            Overrides retryable_errors.
    """

    max_retries: int = 3
    delay: float = 1.0
    backoff: float = 2.0
    max_delay: float = 60.0
    retryable_errors: list[str] | None = None
    abort_on: list[str] | None = None


@dataclass
class RetryState:
    """Current retry state for a step.

    Attributes:
        step_name: Name of the step being retried.
        attempt: Current attempt number (1-based).
        max_retries: Maximum retries configured.
        last_error: Error from the last attempt.
        error_class: Classification of the last error.
        delay: Current delay before next retry.
        started_at: Timestamp of first attempt.
    """

    step_name: str
    attempt: int = 1
    max_retries: int = 3
    last_error: str = ""
    error_class: ErrorClass = ErrorClass.UNKNOWN
    delay: float = 0.0
    started_at: float = 0.0


class RetryEngine:
    """Manages retry logic for workflow step execution.

    Evaluates whether a failed step should be retried based on
    the configured policy and the classification of the error.

    Usage:
        >>> engine = RetryEngine()
        >>> policy = RetryPolicy(max_retries=3, delay=1.0, backoff=2.0)
        >>> state = RetryState(step_name="build")
        >>> decision, updated_state = engine.evaluate(state, result, policy)
        >>> if decision == RetryDecision.RETRY:
        ...     wait_time = engine.compute_delay(updated_state, policy)
        ...     time.sleep(wait_time)
    """

    # ------------------------------------------------------------------
    # Error classification
    # ------------------------------------------------------------------

    def classify_error(self, result: StepResult) -> ErrorClass:
        """Classify a step execution error.

        Args:
            result: The step execution result.

        Returns:
            ErrorClass based on error message patterns.
        """
        error_msg = (result.error or "").lower()
        message = result.message.lower()

        if any(kw in error_msg or kw in message for kw in ["timeout", "timed out"]):
            return ErrorClass.TIMEOUT

        if any(kw in error_msg or kw in message for kw in [
            "rate limit", "too many requests", "throttl",
        ]):
            return ErrorClass.TRANSIENT

        if any(kw in error_msg or kw in message for kw in [
            "connection", "network", "temporarily", "try again",
        ]):
            return ErrorClass.TRANSIENT

        if any(kw in error_msg or kw in message for kw in ["capability", "unresolved"]):
            return ErrorClass.CAPABILITY_UNRESOLVED

        if any(kw in error_msg or kw in message for kw in ["plugin", "not found"]):
            return ErrorClass.PLUGIN_ERROR

        if any(kw in error_msg or kw in message for kw in ["contract", "constraint", "violation"]):
            return ErrorClass.CONTRACT_VIOLATION

        if any(kw in error_msg or kw in message for kw in ["verification", "test failed", "lint"]):
            return ErrorClass.VERIFICATION_FAILURE

        return ErrorClass.UNKNOWN

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        state: RetryState,
        result: StepResult,
        policy: RetryPolicy,
    ) -> tuple[RetryDecision, RetryState]:
        """Evaluate whether to retry a failed step.

        Args:
            state: Current retry state.
            result: The failed step result.
            policy: Retry policy configuration.

        Returns:
            Tuple of (RetryDecision, updated RetryState).
        """
        # Classify the error
        error_class = self.classify_error(result)
        state.error_class = error_class
        state.last_error = result.error or result.message

        # Check abort conditions
        if policy.abort_on:
            if error_class.value in policy.abort_on:
                logger.warning(
                    "Aborting retry for '%s': error class '%s' is in abort list",
                    state.step_name,
                    error_class.value,
                )
                return RetryDecision.ABORT, state

        # Check retryable conditions
        if policy.retryable_errors:
            if error_class.value not in policy.retryable_errors:
                logger.warning(
                    "Not retrying '%s': error class '%s' is not retryable",
                    state.step_name,
                    error_class.value,
                )
                return RetryDecision.ESCALATE, state

        # Check max retries
        if state.attempt >= state.max_retries:
            logger.warning(
                "Max retries (%d) reached for '%s'",
                state.max_retries,
                state.step_name,
            )
            return RetryDecision.ABORT, state

        # Check for contract violations (always escalate, never retry)
        if error_class in (ErrorClass.CONTRACT_VIOLATION, ErrorClass.CAPABILITY_UNRESOLVED):
            return RetryDecision.ESCALATE, state

        # Decision: retry
        state.attempt += 1
        return RetryDecision.RETRY, state

    # ------------------------------------------------------------------
    # Delay computation
    # ------------------------------------------------------------------

    def compute_delay(
        self,
        state: RetryState,
        policy: RetryPolicy,
    ) -> float:
        """Compute the delay before the next retry attempt.

        Uses exponential backoff: ``delay * backoff^(attempt - 1)``

        Args:
            state: Current retry state.
            policy: Retry policy.

        Returns:
            Delay in seconds.
        """
        delay = policy.delay * (policy.backoff ** (state.attempt - 2))
        delay = min(delay, policy.max_delay)
        state.delay = delay
        return delay

    def wait_and_retry(
        self,
        state: RetryState,
        policy: RetryPolicy,
    ) -> None:
        """Wait the computed delay (blocking).

        Args:
            state: Current retry state.
            policy: Retry policy.
        """
        delay = self.compute_delay(state, policy)
        logger.info(
            "Retrying '%s' (attempt %d/%d) in %.1fs...",
            state.step_name,
            state.attempt,
            state.max_retries,
            delay,
        )
        time.sleep(delay)

    # ------------------------------------------------------------------
    # Abort policies
    # ------------------------------------------------------------------

    def should_abort(
        self,
        result: StepResult,
        policy: RetryPolicy,
        consecutive_failures: int = 0,
        max_consecutive_failures: int = 5,
    ) -> bool:
        """Determine if execution should abort based on the result.

        Args:
            result: The step execution result.
            policy: Retry policy.
            consecutive_failures: Number of consecutive failures.
            max_consecutive_failures: Max consecutive failures before abort.

        Returns:
            True if execution should abort.
        """
        # Plugin not found is always fatal
        if "not found" in (result.error or "").lower():
            return True

        # Too many consecutive failures
        if consecutive_failures >= max_consecutive_failures:
            return True

        # Check abort-on errors
        if policy.abort_on:
            error_class = self.classify_error(result)
            if error_class.value in policy.abort_on:
                return True

        return False

    def classify_step_result(self, result: StepResult) -> ErrorClass:
        """Convenience method to classify a step result.

        Args:
            result: The step execution result.

        Returns:
            ErrorClass.
        """
        return self.classify_error(result)
