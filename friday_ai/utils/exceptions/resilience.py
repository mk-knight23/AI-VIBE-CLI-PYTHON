from typing import Any
from .base import FridayError


class CircuitOpenError(FridayError):
    """Circuit breaker is open."""

    def __init__(
        self,
        message: str = "Circuit breaker is open",
        failure_count: int | None = None,
        last_failure: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if failure_count is not None:
            details["failure_count"] = failure_count
        if last_failure:
            details["last_failure"] = last_failure
        super().__init__(
            message=message, code="CIRCUIT_OPEN", details=details, retryable=True, **kwargs
        )
        self.failure_count = failure_count
        self.last_failure = last_failure


class CircuitBreakerHalfOpenError(FridayError):
    """Circuit breaker is half-open (testing recovery)."""

    def __init__(self, message: str = "Circuit breaker is half-open", **kwargs: Any) -> None:
        super().__init__(message=message, code="CIRCUIT_HALF_OPEN", retryable=True, **kwargs)


class TimeoutError(FridayError):
    """Operation timed out."""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if operation:
            details["operation"] = operation
        if timeout is not None:
            details["timeout_seconds"] = timeout
        super().__init__(message=message, code="TIMEOUT", details=details, retryable=True, **kwargs)
        self.operation = operation
        self.timeout = timeout


class RetryExhaustedError(FridayError):
    """All retry attempts exhausted."""

    def __init__(
        self,
        message: str,
        attempts: int,
        last_error: Exception | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        details["attempts"] = attempts
        if last_error:
            details["last_error"] = str(last_error)
            details["last_error_type"] = type(last_error).__name__
        super().__init__(
            message=message, code="RETRY_EXHAUSTED", details=details, retryable=False, **kwargs
        )
        self.attempts = attempts
        self.last_error = last_error
