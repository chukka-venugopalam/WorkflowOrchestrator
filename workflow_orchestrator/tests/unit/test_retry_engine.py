"""Unit tests for RetryEngine."""

from __future__ import annotations

from workflow_orchestrator.execution.retry_engine import (
    ErrorClass,
    RetryDecision,
    RetryEngine,
    RetryPolicy,
    RetryState,
)
from workflow_orchestrator.models import StepResult, StepStatus


class TestRetryEngine:
    """Tests for the RetryEngine."""

    def setup_method(self) -> None:
        self.engine = RetryEngine()

    def _make_result(
        self,
        error: str = "",
        message: str = "",
        status: StepStatus = StepStatus.FAILURE,
    ) -> StepResult:
        return StepResult(
            step_name="test",
            plugin="terminal",
            status=status,
            error=error,
            message=message,
        )

    def test_classify_timeout(self) -> None:
        """Test classification of timeout errors."""
        result = self._make_result(error="Operation timed out")
        assert self.engine.classify_error(result) == ErrorClass.TIMEOUT

        result2 = self._make_result(message="timed out after 30s")
        assert self.engine.classify_error(result2) == ErrorClass.TIMEOUT

    def test_classify_transient_network(self) -> None:
        """Test classification of transient network errors."""
        result = self._make_result(error="Connection refused")
        assert self.engine.classify_error(result) == ErrorClass.TRANSIENT

    def test_classify_transient_rate_limit(self) -> None:
        """Test classification of rate limit errors."""
        result = self._make_result(error="Rate limit exceeded")
        assert self.engine.classify_error(result) == ErrorClass.TRANSIENT

    def test_classify_plugin_error(self) -> None:
        """Test classification of plugin errors."""
        result = self._make_result(error="Plugin 'foo' not found")
        assert self.engine.classify_error(result) == ErrorClass.PLUGIN_ERROR

    def test_classify_capability_unresolved(self) -> None:
        """Test classification of capability unresolved errors."""
        result = self._make_result(error="Capability 'codegen' unresolved")
        assert self.engine.classify_error(result) == ErrorClass.CAPABILITY_UNRESOLVED

    def test_classify_unknown(self) -> None:
        """Test classification of unknown errors."""
        result = self._make_result(error="Something completely unexpected")
        assert self.engine.classify_error(result) == ErrorClass.UNKNOWN

    def test_evaluate_retry(self) -> None:
        """Test that retryable errors trigger RETRY decision."""
        state = RetryState(step_name="test", max_retries=3)
        result = self._make_result(error="Temporary network issue")
        policy = RetryPolicy(max_retries=3, delay=1.0, backoff=2.0)

        decision, new_state = self.engine.evaluate(state, result, policy)
        assert decision == RetryDecision.RETRY
        assert new_state.attempt == 2

    def test_evaluate_abort_max_retries(self) -> None:
        """Test that max retries reached triggers ABORT."""
        state = RetryState(step_name="test", max_retries=1, attempt=1)
        result = self._make_result(error="Temporary issue")
        policy = RetryPolicy(max_retries=1, delay=1.0, backoff=2.0)

        # First attempt... evaluates and since attempt >= max_retries, aborts
        decision, _ = self.engine.evaluate(state, result, policy)
        assert decision == RetryDecision.ABORT

    def test_evaluate_abort_on_error_class(self) -> None:
        """Test that abort_on prevents retry for matching errors."""
        state = RetryState(step_name="test", max_retries=5)
        result = self._make_result(error="Plugin 'xyz' not found")
        policy = RetryPolicy(
            max_retries=5,
            abort_on=["plugin_error"],
        )

        decision, _ = self.engine.evaluate(state, result, policy)
        assert decision == RetryDecision.ABORT

    def test_evaluate_escalate_non_retryable(self) -> None:
        """Test that non-retryable errors escalate."""
        state = RetryState(step_name="test", max_retries=5)
        result = self._make_result(error="Contract violation")
        policy = RetryPolicy(
            max_retries=5,
            retryable_errors=["transient", "timeout"],
        )

        decision, _ = self.engine.evaluate(state, result, policy)
        assert decision == RetryDecision.ESCALATE

    def test_compute_delay_exponential(self) -> None:
        """Test exponential backoff delay computation."""
        state = RetryState(step_name="test", attempt=2)
        policy = RetryPolicy(delay=1.0, backoff=2.0)

        # Second attempt: delay * 2^(2-2) = 1.0 * 1 = 1.0
        delay = self.engine.compute_delay(state, policy)
        assert delay == 1.0

        state.attempt = 3
        delay = self.engine.compute_delay(state, policy)
        assert delay == 2.0  # 1.0 * 2^(3-2) = 2.0

        state.attempt = 4
        delay = self.engine.compute_delay(state, policy)
        assert delay == 4.0  # 1.0 * 2^(4-2) = 4.0

    def test_compute_delay_capped(self) -> None:
        """Test that delay doesn't exceed max_delay."""
        state = RetryState(step_name="test", attempt=10)
        policy = RetryPolicy(delay=1.0, backoff=2.0, max_delay=30.0)

        delay = self.engine.compute_delay(state, policy)
        assert delay <= 30.0

    def test_should_abort_plugin_not_found(self) -> None:
        """Test that plugin not found always aborts."""
        result = self._make_result(error="Plugin 'foo' not found")
        policy = RetryPolicy()
        assert self.engine.should_abort(result, policy)

    def test_should_abort_consecutive_failures(self) -> None:
        """Test that too many consecutive failures abort."""
        result = self._make_result(error="Some error")
        policy = RetryPolicy()
        assert self.engine.should_abort(result, policy, consecutive_failures=10, max_consecutive_failures=5)

    def test_should_not_abort_normal(self) -> None:
        """Test that normal errors don't trigger abort."""
        result = self._make_result(error="Transient error")
        policy = RetryPolicy()
        assert not self.engine.should_abort(result, policy)

    def test_classify_step_result_convenience(self) -> None:
        """Test classify_step_result convenience method."""
        result = self._make_result(error="timed out")
        assert self.engine.classify_step_result(result) == ErrorClass.TIMEOUT
