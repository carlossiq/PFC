"""
Tests for API routes.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """
    Fornece TestClient para testes de rota.
    """
    return TestClient(app)


def test_health_check_route(client):
    """
    Testa rota de health check.
    """
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "run_id" in data


def test_response_includes_run_id(client):
    """
    Verifica que responses incluem run_id.
    """
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
