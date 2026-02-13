from typing import Any
from .base import FridayError


class RateLimitError(FridayError):
    """Rate limit exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit: int | None = None,
        reset_after: float | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if limit is not None:
            details["limit"] = limit
        if reset_after is not None:
            details["reset_after_seconds"] = reset_after
        super().__init__(
            message=message, code="RATE_LIMIT_EXCEEDED", details=details, retryable=True, **kwargs
        )
        self.limit = limit
        self.reset_after = reset_after


class ResourceExhaustedError(FridayError):
    """Resource exhaustion (memory, disk, connections, etc.)."""

    def __init__(
        self,
        message: str,
        resource_type: str | None = None,
        current_usage: float | None = None,
        limit: float | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if resource_type:
            details["resource_type"] = resource_type
        if current_usage is not None:
            details["current_usage"] = current_usage
        if limit is not None:
            details["limit"] = limit
        super().__init__(
            message=message, code="RESOURCE_EXHAUSTED", details=details, retryable=False, **kwargs
        )
        self.resource_type = resource_type
        self.current_usage = current_usage
        self.limit = limit


class QuotaExceededError(FridayError):
    """API quota exceeded."""

    def __init__(
        self,
        message: str = "API quota exceeded",
        quota: int | None = None,
        used: int | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if quota is not None:
            details["quota"] = quota
        if used is not None:
            details["used"] = used
        super().__init__(
            message=message, code="QUOTA_EXCEEDED", details=details, retryable=False, **kwargs
        )
        self.quota = quota
        self.used = used
