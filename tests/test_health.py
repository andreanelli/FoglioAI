"""Tests for health check endpoint."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI application.

    Returns:
        TestClient: FastAPI test client
    """
    return TestClient(app)


def test_health_check_healthy(client: TestClient) -> None:
    """Test health check endpoint when all services are healthy.

    Args:
        client (TestClient): FastAPI test client
    """
    with patch("app.main.redis_client") as mock_redis:
        # Mock Redis connection check to return True
        mock_redis.check_connection = MagicMock(return_value=True)

        # Make request to health check endpoint
        response = client.get("/health")

        # Assert response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "foglioai"
        assert "version" in data
        assert data["dependencies"]["redis"]["status"] == "healthy"


def test_health_check_unhealthy(client: TestClient) -> None:
    """Test health check endpoint when Redis is unhealthy.

    Args:
        client (TestClient): FastAPI test client
    """
    with patch("app.main.redis_client") as mock_redis:
        # Mock Redis connection check to return False
        mock_redis.check_connection = MagicMock(return_value=False)

        # Make request to health check endpoint
        response = client.get("/health")

        # Assert response
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["service"] == "foglioai"
        assert "version" in data
        assert data["dependencies"]["redis"]["status"] == "unhealthy" 