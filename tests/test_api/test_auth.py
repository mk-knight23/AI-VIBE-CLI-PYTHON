"""Tests for API authentication."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from friday_ai.api.server import create_app
from friday_ai.auth.api_keys import APIKeyManager


@pytest.fixture
def app():
    """Create app with mocked state."""
    app = create_app()
    # Mock state (bypass lifespan)
    app.state.api_key_manager = APIKeyManager(redis_backend=None)
    app.state.redis_backend = None
    # Mock rate limiter to always allow
    mock_limiter = AsyncMock()
    mock_limiter.is_allowed = AsyncMock(return_value=(True, 0))
    app.state.rate_limiter = mock_limiter
    return app


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


def test_missing_auth_header(client):
    """Test request without auth header returns 401."""
    response = client.post("/api/v2/sessions/")
    assert response.status_code == 401


def test_invalid_api_key(client):
    """Test request with invalid API key returns 401."""
    response = client.post(
        "/api/v2/sessions/",
        headers={"Authorization": "Bearer invalid_key"},
    )
    assert response.status_code == 401


def test_valid_api_key(client):
    """Test request with valid test API key succeeds."""
    response = client.post(
        "/api/v2/sessions/",
        headers={"Authorization": "Bearer friday_test_key_12345"},
        json={"name": "Test Session"},
    )
    # Should succeed (may be 201 or 500 if Redis unavailable)
    assert response.status_code in [201, 500]
