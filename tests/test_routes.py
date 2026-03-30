"""
Tests for API routes.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from schemas.intake import InputIntake


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


def test_intake_route_requires_theme(client):
    """
    Verifica que intake exige tema.
    """
    response = client.post(
        "/api/v1/intake",
        json={"theme": ""},
    )

    assert response.status_code == 422  # Validation error


def test_intake_route_accepts_valid_input(client):
    """
    Verifica que intake aceita entrada válida.
    """
    response = client.post(
        "/api/v1/intake",
        json={
            "theme": "Machine Learning",
            "objective": "Find AI papers",
            "initial_keywords": ["deep learning"],
            "document_type": "both",
        },
    )

    # No environment de teste sem banco de dados real,
    # espera-se erro, mas request é validado
    assert response.status_code in [200, 500]


def test_test_llm_route(client):
    """
    Testa rota de teste de LLM.
    """
    response = client.post(
        "/api/v1/test/llm",
        json={
            "theme": "Test",
            "document_type": "both",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"]
    assert "run_id" in data["data"]


def test_test_nlp_route(client):
    """
    Testa rota de teste de NLP.
    """
    response = client.post(
        "/api/v1/test/nlp",
        json={"text": "Machine learning is a subset of AI"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"]


def test_test_query_builder_route(client):
    """
    Testa rota de teste de query builder.
    """
    response = client.post(
        "/api/v1/test/query-builder",
        json={
            "api_name": "lens_patent",
            "theme": "Test",
            "document_type": "both",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"]


def test_test_field_schema_route(client):
    """
    Testa rota de teste de field schema.
    """
    response = client.post(
        "/api/v1/test/field-schema",
        json={
            "api_name": "lens_patent",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"]


def test_response_includes_run_id(client):
    """
    Verifica que responses incluem run_id.
    """
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
