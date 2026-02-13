from __future__ import annotations
import uuid
from typing import Any


class FridayError(Exception):
    """Base exception for all Friday AI errors."""

    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        details: dict[str, Any] | None = None,
        retryable: bool = False,
        trace_id: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.retryable = retryable
        self.trace_id = trace_id or str(uuid.uuid4())[:8]
        self.cause = cause

    def __str__(self) -> str:
        parts = [f"[{self.code}] {self.message}"]
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            parts.append(f"({detail_str})")
        if self.cause:
            parts.append(f"[caused by: {self.cause}]")
        return " ".join(parts)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"code={self.code!r}, "
            f"message={self.message!r}, "
            f"retryable={self.retryable}, "
            f"trace_id={self.trace_id!r}"
            f")"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        return {
            "type": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "retryable": self.retryable,
            "trace_id": self.trace_id,
            "cause": str(self.cause) if self.cause else None,
        }

    def with_context(self, **kwargs: Any) -> FridayError:
        """Create a new error with additional context."""
        new_details = {**self.details, **kwargs}
        return self.__class__(
            message=self.message,
            code=self.code,
            details=new_details,
            retryable=self.retryable,
            trace_id=self.trace_id,
            cause=self.cause,
        )


class AgentError(FridayError):
    """Legacy agent error - kept for backward compatibility."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="AGENT_ERROR",
            details=details,
            cause=cause,
        )
