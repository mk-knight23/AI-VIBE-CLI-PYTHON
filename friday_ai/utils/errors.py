"""Enhanced error hierarchy for Friday AI.

Provides industry-standard exception taxonomy with error codes,
retryable flags, structured context, and trace ID support.
"""

from __future__ import annotations

import uuid
from typing import Any


class FridayError(Exception):
    """Base exception for all Friday AI errors.

    Features:
    - Machine-readable error codes
    - Human-readable messages
    - Structured context (details dict)
    - Retryable flag for automatic retry decisions
    - Trace ID for distributed tracing
    - Exception chaining support

    Example:
        raise ToolExecutionError(
            message="Failed to execute shell command",
            code="TOOL_EXECUTION_FAILED",
            details={"tool": "shell", "command": "[REDACTED]", "exit_code": 1},
            retryable=False
        )
    """

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


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigError(FridayError):
    """Configuration-related errors."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        config_file: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if config_key:
            details["config_key"] = config_key
        if config_file:
            details["config_file"] = config_file
        super().__init__(
            message=message,
            code="CONFIG_ERROR",
            details=details,
            retryable=False,
            **kwargs,
        )
        self.config_key = config_key
        self.config_file = config_file


class ValidationError(FridayError):
    """Input validation errors."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details=details,
            retryable=False,
            **kwargs,
        )
        self.field = field
        self.value = value


# =============================================================================
# Tool Execution Errors
# =============================================================================


class ToolExecutionError(FridayError):
    """Tool execution failures."""

    def __init__(
        self,
        message: str,
        tool: str | None = None,
        exit_code: int | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if tool:
            details["tool"] = tool
        if exit_code is not None:
            details["exit_code"] = exit_code
        # Tool errors are generally not retryable unless specified
        retryable = kwargs.pop("retryable", False)
        super().__init__(
            message=message,
            code="TOOL_EXECUTION_FAILED",
            details=details,
            retryable=retryable,
            **kwargs,
        )
        self.tool = tool
        self.exit_code = exit_code


class ToolNotFoundError(FridayError):
    """Requested tool not found."""

    def __init__(self, tool: str, **kwargs: Any) -> None:
        super().__init__(
            message=f"Tool not found: {tool}",
            code="TOOL_NOT_FOUND",
            details={"tool": tool},
            retryable=False,
            **kwargs,
        )
        self.tool = tool


class ToolTimeoutError(FridayError):
    """Tool execution timed out."""

    def __init__(
        self,
        message: str,
        tool: str | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if tool:
            details["tool"] = tool
        if timeout is not None:
            details["timeout_seconds"] = timeout
        # Timeouts are retryable (might succeed on retry)
        super().__init__(
            message=message,
            code="TOOL_TIMEOUT",
            details=details,
            retryable=True,
            **kwargs,
        )
        self.tool = tool
        self.timeout = timeout


# =============================================================================
# Security Errors
# =============================================================================


class SecurityError(FridayError):
    """Base class for security-related errors."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("retryable", False)
        super().__init__(message, **kwargs)


class AuthenticationError(SecurityError):
    """Authentication failures."""

    def __init__(self, message: str = "Authentication failed", **kwargs: Any) -> None:
        super().__init__(
            message=message,
            code="AUTHENTICATION_FAILED",
            **kwargs,
        )


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
        # Remove 'details' from kwargs if it exists to avoid duplicate
        kwargs.pop("details", None)
        super().__init__(
            message=message,
            code="AUTHORIZATION_FAILED",
            details=details,
            **kwargs,
        )
        self.resource = resource
        self.action = action


class SecretNotFoundError(SecurityError):
    """Requested secret not found in vault."""

    def __init__(self, key: str, **kwargs: Any) -> None:
        details = kwargs.pop("details", {}) or {}
        details["key"] = key
        super().__init__(
            message=f"Secret not found: {key}",
            code="SECRET_NOT_FOUND",
            details=details,
            **kwargs,
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


# =============================================================================
# Resource & Rate Limiting Errors
# =============================================================================


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
        # Rate limit errors are retryable after the reset period
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            details=details,
            retryable=True,
            **kwargs,
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
            message=message,
            code="RESOURCE_EXHAUSTED",
            details=details,
            retryable=False,  # Usually requires manual intervention
            **kwargs,
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
            message=message,
            code="QUOTA_EXCEEDED",
            details=details,
            retryable=False,
            **kwargs,
        )
        self.quota = quota
        self.used = used


# =============================================================================
# Circuit Breaker & Resilience Errors
# =============================================================================


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
        # Circuit open errors are retryable (circuit will close eventually)
        super().__init__(
            message=message,
            code="CIRCUIT_OPEN",
            details=details,
            retryable=True,
            **kwargs,
        )
        self.failure_count = failure_count
        self.last_failure = last_failure


class CircuitBreakerHalfOpenError(FridayError):
    """Circuit breaker is half-open (testing recovery)."""

    def __init__(self, message: str = "Circuit breaker is half-open", **kwargs: Any) -> None:
        super().__init__(
            message=message,
            code="CIRCUIT_HALF_OPEN",
            retryable=True,
            **kwargs,
        )


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
        super().__init__(
            message=message,
            code="TIMEOUT",
            details=details,
            retryable=True,
            **kwargs,
        )
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
            message=message,
            code="RETRY_EXHAUSTED",
            details=details,
            retryable=False,
            **kwargs,
        )
        self.attempts = attempts
        self.last_error = last_error


# =============================================================================
# Dependency & Network Errors
# =============================================================================


class DependencyError(FridayError):
    """External dependency failures."""

    def __init__(
        self,
        message: str,
        dependency: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if dependency:
            details["dependency"] = dependency
        # Dependency errors are often transient and retryable
        kwargs.setdefault("retryable", True)
        super().__init__(
            message=message,
            code="DEPENDENCY_ERROR",
            details=details,
            **kwargs,
        )
        self.dependency = dependency


class ConnectionError(FridayError):
    """Network connection failures."""

    def __init__(
        self,
        message: str,
        host: str | None = None,
        port: int | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if host:
            details["host"] = host
        if port is not None:
            details["port"] = port
        super().__init__(
            message=message,
            code="CONNECTION_ERROR",
            details=details,
            retryable=True,
            **kwargs,
        )
        self.host = host
        self.port = port


class DatabaseError(FridayError):
    """Database-related errors."""

    def __init__(
        self,
        message: str,
        backend: str | None = None,
        query: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if backend:
            details["backend"] = backend
        if query:
            # Only include query preview for security
            details["query_preview"] = query[:100] + "..." if len(query) > 100 else query
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            details=details,
            retryable=True,  # DB errors are often transient
            **kwargs,
        )
        self.backend = backend
        self.query = query


# =============================================================================
# Session Errors
# =============================================================================


class SessionError(FridayError):
    """Session management errors."""

    def __init__(self, message: str, session_id: str | None = None, **kwargs: Any) -> None:
        details = kwargs.pop("details", {}) or {}
        if session_id:
            details["session_id"] = session_id
        super().__init__(
            message=message,
            code="SESSION_ERROR",
            details=details,
            retryable=False,
            **kwargs,
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

    def __init__(
        self,
        session_id: str,
        expired_at: str | None = None,
        **kwargs: Any,
    ) -> None:
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


# =============================================================================
# Legacy Compatibility
# =============================================================================


class AgentError(FridayError):
    """Legacy agent error - kept for backward compatibility.

    Deprecated: Use specific error classes instead.
    """

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


# Export all error classes
__all__ = [
    # Base
    "FridayError",
    # Config
    "ConfigError",
    "ValidationError",
    # Tools
    "ToolExecutionError",
    "ToolNotFoundError",
    "ToolTimeoutError",
    # Security
    "SecurityError",
    "AuthenticationError",
    "AuthorizationError",
    "SecretNotFoundError",
    "PathTraversalError",
    "CommandInjectionError",
    "SQLInjectionError",
    # Resources
    "RateLimitError",
    "ResourceExhaustedError",
    "QuotaExceededError",
    # Resilience
    "CircuitOpenError",
    "CircuitBreakerHalfOpenError",
    "TimeoutError",
    "RetryExhaustedError",
    # Dependencies
    "DependencyError",
    "ConnectionError",
    "DatabaseError",
    # Session
    "SessionError",
    "SessionNotFoundError",
    "SessionExpiredError",
    # Legacy
    "AgentError",
]
