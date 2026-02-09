"""Tests for health check endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport

from friday_ai.api.server import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_health_endpoint(app):
    """Test basic health check returns 200."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "2.0.0"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_liveness_endpoint(app):
    """Test liveness probe."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/live")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


@pytest.mark.asyncio
async def test_health_has_timestamp(app):
    """Test health response includes timestamp."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "timestamp" in data
    assert isinstance(data["timestamp"], str)
