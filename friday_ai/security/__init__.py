"""Security package for Friday AI.

Provides audit logging, secret management, and input validation
for production-grade security.
"""

from friday_ai.security.audit_logger import AuditEventType, AuditLogger, AuditRecord
from friday_ai.security.secret_manager import SecretManager, SecretNotFoundError
from friday_ai.security.validators import (
    CommandInjectionError,
    InputValidator,
    PathTraversalError,
    SQLInjectionError,
    ValidatedCommand,
    ValidatedPath,
    ValidatedSQL,
    ValidatedURL,
)

__all__ = [
    # Audit Logger
    "AuditLogger",
    "AuditRecord",
    "AuditEventType",
    # Secret Manager
    "SecretManager",
    "SecretNotFoundError",
    # Validators
    "InputValidator",
    "ValidatedPath",
    "ValidatedCommand",
    "ValidatedSQL",
    "ValidatedURL",
    "PathTraversalError",
    "CommandInjectionError",
    "SQLInjectionError",
]
