from typing import Any
from .base import FridayError


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
        kwargs.setdefault("retryable", True)
        super().__init__(message=message, code="DEPENDENCY_ERROR", details=details, **kwargs)
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
            message=message, code="CONNECTION_ERROR", details=details, retryable=True, **kwargs
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
            details["query_preview"] = query[:100] + "..." if len(query) > 100 else query
        super().__init__(
            message=message, code="DATABASE_ERROR", details=details, retryable=True, **kwargs
        )
        self.backend = backend
        self.query = query
