import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Set test environment before importing app
os.environ["ENVIRONMENT"] = "test"
os.environ["DOCKER_ENV"] = "false"

from src.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health endpoint with mocked dependencies."""
    with patch(
        "src.repositories.health_repository.HealthRepository.get_status"
    ) as mock_get_status:
        # Mock the repository to return healthy status
        mock_get_status.return_value = "healthy"

        client = TestClient(app)
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "healthy"
        assert "timestamp" in response_data


@pytest.mark.asyncio
async def test_health_endpoint_unhealthy():
    """Test health endpoint when services are unhealthy."""
    with patch(
        "src.repositories.health_repository.HealthRepository.get_status"
    ) as mock_get_status:
        # Mock the repository to return unhealthy status
        mock_get_status.return_value = "unhealthy"

        client = TestClient(app)
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "unhealthy"
        assert "timestamp" in response_data
