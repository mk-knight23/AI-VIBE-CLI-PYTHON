"""Enhanced error hierarchy for Friday AI.

Provides industry-standard exception taxonomy with error codes,
retryable flags, structured context, and trace ID support.

Note: This module is now a wrapper around the friday_ai.utils.exceptions package.
"""

from friday_ai.utils.exceptions import (
    FridayError,
    ConfigError,
    ValidationError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolTimeoutError,
    SecurityError,
    AuthenticationError,
    AuthorizationError,
    SecretNotFoundError,
    PathTraversalError,
    CommandInjectionError,
    SQLInjectionError,
    RateLimitError,
    ResourceExhaustedError,
    QuotaExceededError,
    CircuitOpenError,
    CircuitBreakerHalfOpenError,
    TimeoutError,
    RetryExhaustedError,
    DependencyError,
    ConnectionError,
    DatabaseError,
    SessionError,
    SessionNotFoundError,
    SessionExpiredError,
    AgentError,
)

# Export all error classes for backward compatibility
__all__ = [
    "FridayError",
    "ConfigError",
    "ValidationError",
    "ToolExecutionError",
    "ToolNotFoundError",
    "ToolTimeoutError",
    "SecurityError",
    "AuthenticationError",
    "AuthorizationError",
    "SecretNotFoundError",
    "PathTraversalError",
    "CommandInjectionError",
    "SQLInjectionError",
    "RateLimitError",
    "ResourceExhaustedError",
    "QuotaExceededError",
    "CircuitOpenError",
    "CircuitBreakerHalfOpenError",
    "TimeoutError",
    "RetryExhaustedError",
    "DependencyError",
    "ConnectionError",
    "DatabaseError",
    "SessionError",
    "SessionNotFoundError",
    "SessionExpiredError",
    "AgentError",
]
