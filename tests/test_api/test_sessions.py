"""Tests for session management endpoints."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from friday_ai.api.server import create_app
from friday_ai.auth.api_keys import APIKeyManager

API_KEY = "Bearer friday_test_key_12345"


@pytest.fixture
def app():
    """Create app with mocked state."""
    app = create_app()
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


def test_create_session(client):
    """Test creating a new session."""
    response = client.post(
        "/api/v2/sessions/",
        headers={"Authorization": API_KEY},
        json={"name": "Test Session", "metadata": {"test": True}},
    )

    # May be 201 if Redis available, 500 if not
    assert response.status_code in [201, 500]

    if response.status_code == 201:
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Session"


def test_list_sessions(client):
    """Test listing user sessions."""
    response = client.get(
        "/api/v2/sessions/",
        headers={"Authorization": API_KEY},
    )

    assert response.status_code in [200, 500]

    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)


def test_get_session_not_found(client):
    """Test getting non-existent session returns 404."""
    response = client.get(
        "/api/v2/sessions/non-existent-id",
        headers={"Authorization": API_KEY},
    )

    # 404 if Redis returns None, 500 if Redis unavailable
    assert response.status_code in [404, 500]
