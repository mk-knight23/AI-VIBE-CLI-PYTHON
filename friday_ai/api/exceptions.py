"""Standardized API exception handling.

Provides consistent error response format with trace IDs across all API endpoints.
Integrates with FridayError hierarchy for proper error classification.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from friday_ai.api.models.responses import ErrorResponse, ErrorDetail
from friday_ai.utils.errors import FridayError

logger = logging.getLogger(__name__)


class APIError(HTTPException):
    """Base API exception with standardized error format.

    Features:
    - Consistent error response structure
    - Automatic trace ID generation
    - Integration with FridayError hierarchy
    - HTTP status code mapping

    Example:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Tool not found",
            code="TOOL_NOT_FOUND",
            details={"tool": "shell"}
        )
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        code: str = "API_ERROR",
        details: dict[str, Any] | None = None,
        trace_id: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize API error.

        Args:
            status_code: HTTP status code
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error context
            trace_id: Trace ID for debugging (auto-generated if None)
            headers: Additional response headers
        """
        self.trace_id = trace_id or str(uuid.uuid4())[:8]
        self.error_detail = ErrorDetail(
            code=code,
            message=message,
            field=details.get("field") if details else None,
        )
        self.details = details or {}

        super().__init__(
            status_code=status_code,
            detail=message,
            headers=headers,
        )


    def to_response(self) -> JSONResponse:
        """Convert to JSONResponse."""
        return JSONResponse(
            status_code=self.status_code,
            content=ErrorResponse(
                success=False,
                error=self.error_detail,
                trace_id=self.trace_id,
            ).model_dump(),
            headers=self.headers,
        )


def friday_error_to_api_error(exc: FridayError) -> APIError:
    """Convert FridayError to APIError with appropriate status code.

    Args:
        exc: FridayError instance

    Returns:
        APIError with mapped status code
    """
    # Map error codes to HTTP status codes
    status_map: dict[str, int] = {
        # Security errors
        "AUTHENTICATION_FAILED": status.HTTP_401_UNAUTHORIZED,
        "AUTHORIZATION_FAILED": status.HTTP_403_FORBIDDEN,
        "PATH_TRAVERSAL_DETECTED": status.HTTP_403_FORBIDDEN,
        "COMMAND_INJECTION_DETECTED": status.HTTP_403_FORBIDDEN,
        "SQL_INJECTION_DETECTED": status.HTTP_403_FORBIDDEN,
        # Validation errors
        "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
        "CONFIG_ERROR": status.HTTP_400_BAD_REQUEST,
        # Not found errors
        "TOOL_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "SESSION_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "SECRET_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        # Rate limiting
        "RATE_LIMIT_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
        "QUOTA_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
        # Resource errors
        "RESOURCE_EXHAUSTED": status.HTTP_503_SERVICE_UNAVAILABLE,
        # Circuit breaker
        "CIRCUIT_OPEN": status.HTTP_503_SERVICE_UNAVAILABLE,
        "TIMEOUT": status.HTTP_504_GATEWAY_TIMEOUT,
        # Dependency errors
        "DEPENDENCY_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
        "CONNECTION_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
        "DATABASE_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
        # Tool errors
        "TOOL_EXECUTION_FAILED": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "TOOL_TIMEOUT": status.HTTP_504_GATEWAY_TIMEOUT,
        # Session errors
        "SESSION_EXPIRED": status.HTTP_410_GONE,
        "SESSION_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        # Retry errors
        "RETRY_EXHAUSTED": status.HTTP_503_SERVICE_UNAVAILABLE,
    }

    http_status = status_map.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    return APIError(
        status_code=http_status,
        message=exc.message,
        code=exc.code,
        details=exc.details,
        trace_id=exc.trace_id,
    )


async def friday_error_handler(request: Request, exc: FridayError) -> JSONResponse:
    """Handle FridayError exceptions.

    Args:
        request: FastAPI request
        exc: FridayError exception

    Returns:
        JSONResponse with standardized error format
    """
    api_error = friday_error_to_api_error(exc)

    # Log error with context
    logger.error(
        f"FridayError: {exc.code} - {exc.message}",
        extra={
            "trace_id": exc.trace_id,
            "code": exc.code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return api_error.to_response()


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle APIError exceptions.

    Args:
        request: FastAPI request
        exc: APIError exception

    Returns:
        JSONResponse with standardized error format
    """
    # Log error with context
    logger.error(
        f"APIError: {exc.error_detail.code} - {exc.error_detail.message}",
        extra={
            "trace_id": exc.trace_id,
            "code": exc.error_detail.code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
        },
    )

    return exc.to_response()


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle standard HTTPException with consistent format.

    Args:
        request: FastAPI request
        exc: HTTPException exception

    Returns:
        JSONResponse with standardized error format
    """
    trace_id = str(uuid.uuid4())[:8]

    # Map HTTP status to error codes
    code_map: dict[int, str] = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT",
    }

    error_code = code_map.get(exc.status_code, "HTTP_ERROR")

    # Extract error details
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message", str(detail))
        field = detail.get("field")
        details = {k: v for k, v in detail.items() if k not in ("message", "field")}
    else:
        message = str(detail)
        field = None
        details = {}

    error_detail = ErrorDetail(
        code=error_code,
        message=message,
        field=field,
    )

    # Log warning for client errors, error for server errors
    if exc.status_code < 500:
        logger.warning(
            f"HTTPException {exc.status_code}: {message}",
            extra={
                "trace_id": trace_id,
                "code": error_code,
                "path": request.url.path,
                "method": request.method,
            },
        )
    else:
        logger.error(
            f"HTTPException {exc.status_code}: {message}",
            extra={
                "trace_id": trace_id,
                "code": error_code,
                "path": request.url.path,
                "method": request.method,
            },
        )

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            error=error_detail,
            trace_id=trace_id,
        ).model_dump(),
        headers=exc.headers if hasattr(exc, "headers") else None,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions with consistent format.

    Args:
        request: FastAPI request
        exc: Unhandled exception

    Returns:
        JSONResponse with standardized error format
    """
    trace_id = str(uuid.uuid4())[:8]

    # Log full exception with traceback
    logger.exception(
        f"Unhandled exception: {type(exc).__name__}",
        extra={
            "trace_id": trace_id,
            "path": request.url.path,
            "method": request.method,
            "exc_type": type(exc).__name__,
        },
    )

    # Don't expose internal errors in production
    import os
    is_debug = os.getenv("DEBUG", "false").lower() == "true"

    error_detail = ErrorDetail(
        code="INTERNAL_ERROR",
        message=str(exc) if is_debug else "An unexpected error occurred",
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            success=False,
            error=error_detail,
            trace_id=trace_id,
        ).model_dump(),
    )


def setup_exception_handlers(app) -> None:
    """Register all exception handlers with the FastAPI app.

    Args:
        app: FastAPI application instance
    """
    from fastapi.exceptions import RequestValidationError

    # FridayError handler (highest priority)
    app.add_exception_handler(FridayError, friday_error_handler)

    # APIError handler
    app.add_exception_handler(APIError, api_error_handler)

    # HTTPException handler
    app.add_exception_handler(HTTPException, http_exception_handler)

    # Validation error handler
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle Pydantic validation errors with consistent format."""
        trace_id = str(uuid.uuid4())[:8]

        # Extract first validation error
        errors = exc.errors()
        first_error = errors[0] if errors else {}

        field = ".".join(str(loc) for loc in first_error.get("loc", []))
        message = first_error.get("msg", "Validation error")

        error_detail = ErrorDetail(
            code="VALIDATION_ERROR",
            message=message,
            field=field if field else None,
        )

        logger.warning(
            f"Validation error: {message}",
            extra={
                "trace_id": trace_id,
                "field": field,
                "errors": errors,
            },
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                success=False,
                error=error_detail,
                trace_id=trace_id,
            ).model_dump(),
        )

    app.add_exception_handler(RequestValidationError, validation_error_handler)

    # Generic exception handler (catch-all)
    app.add_exception_handler(Exception, generic_exception_handler)


__all__ = [
    "APIError",
    "friday_error_to_api_error",
    "friday_error_handler",
    "api_error_handler",
    "http_exception_handler",
    "generic_exception_handler",
    "setup_exception_handlers",
]
