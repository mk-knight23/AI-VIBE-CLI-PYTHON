"""Test standardized error handling across API."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from friday_ai.api.exceptions import (
    APIError,
    friday_error_to_api_error,
    setup_exception_handlers,
)
from friday_ai.api.models.responses import ErrorResponse
from friday_ai.utils.errors import (
    AuthenticationError,
    AuthorizationError,
    SessionNotFoundError,
    ToolNotFoundError,
    ValidationError,
    RateLimitError,
)


class TestAPIError:
    """Test APIError exception."""

    def test_api_error_creation(self):
        """Test creating APIError with all parameters."""
        error = APIError(
            status_code=404,
            message="Resource not found",
            code="NOT_FOUND",
            details={"resource": "test"},
            trace_id="abc123",
        )

        assert error.status_code == 404
        assert error.error_detail.message == "Resource not found"
        assert error.error_detail.code == "NOT_FOUND"
        assert error.trace_id == "abc123"
        assert error.details == {"resource": "test"}

    def test_api_error_auto_trace_id(self):
        """Test APIError auto-generates trace ID."""
        error = APIError(
            status_code=500,
            message="Server error",
        )

        assert error.trace_id is not None
        assert len(error.trace_id) == 8

    def test_api_error_to_response(self):
        """Test converting APIError to JSONResponse."""
        error = APIError(
            status_code=404,
            message="Not found",
            code="NOT_FOUND",
        )

        response = error.to_response()

        assert response.status_code == 404
        body = response.body.decode()
        assert "success" in body
        assert "error" in body
        assert "trace_id" in body


class TestFridayErrorMapping:
    """Test FridayError to APIError mapping."""

    def test_authentication_error_mapping(self):
        """Test AuthenticationError maps to 401."""
        friday_err = AuthenticationError(message="Invalid token")
        api_err = friday_error_to_api_error(friday_err)

        assert api_err.status_code == 401
        assert api_err.error_detail.code == "AUTHENTICATION_FAILED"

    def test_authorization_error_mapping(self):
        """Test AuthorizationError maps to 403."""
        friday_err = AuthorizationError(
            message="Access denied",
            resource="session",
            action="delete",
        )
        api_err = friday_error_to_api_error(friday_err)

        assert api_err.status_code == 403
        assert api_err.error_detail.code == "AUTHORIZATION_FAILED"

    def test_not_found_errors_mapping(self):
        """Test not found errors map to 404."""
        errors = [
            SessionNotFoundError(session_id="abc123"),
            ToolNotFoundError(tool="shell"),
        ]

        for error in errors:
            api_err = friday_error_to_api_error(error)
            assert api_err.status_code == 404

    def test_validation_error_mapping(self):
        """Test ValidationError maps to 400."""
        friday_err = ValidationError(
            message="Invalid input",
            field="email",
            value="not-an-email",
        )
        api_err = friday_error_to_api_error(friday_err)

        assert api_err.status_code == 400
        assert api_err.error_detail.code == "VALIDATION_ERROR"

    def test_rate_limit_error_mapping(self):
        """Test RateLimitError maps to 429."""
        friday_err = RateLimitError(
            message="Too many requests",
            limit=100,
            reset_after=60,
        )
        api_err = friday_error_to_api_error(friday_err)

        assert api_err.status_code == 429
        assert api_err.error_detail.code == "RATE_LIMIT_EXCEEDED"


class TestExceptionHandlerIntegration:
    """Test exception handlers with FastAPI integration."""

    @pytest.fixture
    def app(self):
        """Create test app with exception handlers."""
        app = FastAPI()
        setup_exception_handlers(app)

        @app.get("/test/friday-error")
        async def test_friday_error():
            raise SessionNotFoundError(session_id="test123")

        @app.get("/test/api-error")
        async def test_api_error():
            raise APIError(
                status_code=418,
                message="I'm a teapot",
                code="TEAPOT",
            )

        @app.get("/test/http-error")
        async def test_http_error():
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Not found")

        @app.get("/test/generic-error")
        async def test_generic_error():
            raise ValueError("Unexpected error")

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        # raise_server_exceptions=False allows testing 500 error handlers
        return TestClient(app, raise_server_exceptions=False)

    def test_friday_error_handler(self, client):
        """Test FridayError is handled with consistent format."""
        response = client.get("/test/friday-error")

        assert response.status_code == 404
        data = response.json()

        assert data["success"] is False
        assert "error" in data
        assert data["error"]["code"] == "SESSION_NOT_FOUND"
        assert "trace_id" in data
        assert len(data["trace_id"]) == 8

    def test_api_error_handler(self, client):
        """Test APIError is handled correctly."""
        response = client.get("/test/api-error")

        assert response.status_code == 418
        data = response.json()

        assert data["success"] is False
        assert data["error"]["code"] == "TEAPOT"
        assert data["error"]["message"] == "I'm a teapot"
        assert "trace_id" in data

    def test_http_exception_handler(self, client):
        """Test HTTPException is converted to consistent format."""
        response = client.get("/test/http-error")

        assert response.status_code == 404
        data = response.json()

        assert data["success"] is False
        assert data["error"]["code"] == "NOT_FOUND"
        assert "trace_id" in data

    def test_generic_error_handler(self, client):
        """Test generic exceptions are handled safely."""
        response = client.get("/test/generic-error")

        assert response.status_code == 500
        data = response.json()

        assert data["success"] is False
        assert data["error"]["code"] == "INTERNAL_ERROR"
        assert "trace_id" in data
        # Should not expose internal error details
        assert "ValueError" not in data["error"]["message"]


class TestRouterErrorHandling:
    """Test error handling in actual routers."""

    def test_session_not_found_error(self):
        """Test session router uses FridayError."""
        from friday_ai.api.routers.sessions import router, get_session_service
        from friday_ai.api.dependencies import get_current_user, check_rate_limit
        from fastapi.testclient import TestClient
        from fastapi import FastAPI

        app = FastAPI()
        setup_exception_handlers(app)
        app.include_router(router, prefix="/api/v2/sessions")

        # Mock dependencies
        async def mock_user():
            return Mock(id="user123")

        async def mock_rate_limit():
            pass

        async def mock_service():
            from friday_ai.api.services.session_service import SessionService
            from unittest.mock import AsyncMock

            service = Mock(spec=SessionService)
            service.get_session = AsyncMock(return_value=None)
            return service

        app.dependency_overrides[get_current_user] = mock_user
        app.dependency_overrides[check_rate_limit] = mock_rate_limit
        app.dependency_overrides[get_session_service] = mock_service

        client = TestClient(app, raise_server_exceptions=False)

        # This should raise SessionNotFoundError which gets converted
        response = client.get(
            "/api/v2/sessions/abc123", headers={"Authorization": "Bearer test-key"}
        )

        # Should return 404 with consistent error format
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "trace_id" in data
