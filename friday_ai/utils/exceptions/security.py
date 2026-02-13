from typing import Any
from .base import FridayError


class SecurityError(FridayError):
    """Base class for security-related errors."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("retryable", False)
        super().__init__(message, **kwargs)


class AuthenticationError(SecurityError):
    """Authentication failures."""

    def __init__(self, message: str = "Authentication failed", **kwargs: Any) -> None:
        super().__init__(message=message, code="AUTHENTICATION_FAILED", **kwargs)


class AuthorizationError(SecurityError):
    """Authorization failures (insufficient permissions)."""

    def __init__(
        self,
        message: str = "Access denied",
        resource: str | None = None,
        action: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if resource:
            details["resource"] = resource
        if action:
            details["action"] = action
        kwargs.pop("details", None)
        super().__init__(message=message, code="AUTHORIZATION_FAILED", details=details, **kwargs)
        self.resource = resource
        self.action = action


class SecretNotFoundError(SecurityError):
    """Requested secret not found in vault."""

    def __init__(self, key: str, **kwargs: Any) -> None:
        details = kwargs.pop("details", {}) or {}
        details["key"] = key
        super().__init__(
            message=f"Secret not found: {key}", code="SECRET_NOT_FOUND", details=details, **kwargs
        )
        self.key = key


class PathTraversalError(SecurityError):
    """Path traversal attempt detected."""

    def __init__(self, path: str, **kwargs: Any) -> None:
        details = kwargs.pop("details", {}) or {}
        details["path"] = path
        super().__init__(
            message=f"Path traversal detected: {path}",
            code="PATH_TRAVERSAL_DETECTED",
            details=details,
            **kwargs,
        )
        self.path = path


class CommandInjectionError(SecurityError):
    """Command injection attempt detected."""

    def __init__(self, command: str, **kwargs: Any) -> None:
        details = kwargs.pop("details", {}) or {}
        details["command"] = "[REDACTED]"
        super().__init__(
            message="Command injection detected",
            code="COMMAND_INJECTION_DETECTED",
            details=details,
            **kwargs,
        )
        self.command = command


class SQLInjectionError(SecurityError):
    """SQL injection attempt detected."""

    def __init__(self, query: str, **kwargs: Any) -> None:
        details = kwargs.pop("details", {}) or {}
        details["query_preview"] = query[:50] + "..." if len(query) > 50 else query
        super().__init__(
            message="SQL injection detected",
            code="SQL_INJECTION_DETECTED",
            details=details,
            **kwargs,
        )
        self.query = query
