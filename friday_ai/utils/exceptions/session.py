from typing import Any
from .base import FridayError


class SessionError(FridayError):
    """Session management errors."""

    def __init__(self, message: str, session_id: str | None = None, **kwargs: Any) -> None:
        details = kwargs.pop("details", {}) or {}
        if session_id:
            details["session_id"] = session_id

        # Prevent collision if 'code' is passed in kwargs
        kwargs.pop("code", None)

        super().__init__(
            message=message, code="SESSION_ERROR", details=details, retryable=False, **kwargs
        )
        self.session_id = session_id


class SessionNotFoundError(SessionError):
    """Session not found."""

    def __init__(self, session_id: str, **kwargs: Any) -> None:
        super().__init__(
            message=f"Session not found: {session_id}",
            session_id=session_id,
            code="SESSION_NOT_FOUND",
            **kwargs,
        )


class SessionExpiredError(SessionError):
    """Session has expired."""

    def __init__(self, session_id: str, expired_at: str | None = None, **kwargs: Any) -> None:
        details = kwargs.pop("details", {}) or {}
        if expired_at:
            details["expired_at"] = expired_at
        super().__init__(
            message=f"Session expired: {session_id}",
            session_id=session_id,
            code="SESSION_EXPIRED",
            details=details,
            **kwargs,
        )
        self.expired_at = expired_at
