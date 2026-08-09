from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.url import normalize_database_url
from app.main import app, create_app


def test_health_endpoint_is_available_without_authentication() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_render_postgres_url_uses_psycopg_three_driver() -> None:
    assert (
        normalize_database_url("postgresql://ledgerflow:secret@db.internal/ledgerflow")
        == "postgresql+psycopg://ledgerflow:secret@db.internal/ledgerflow"
    )
    assert (
        normalize_database_url("postgres://ledgerflow:secret@db.internal/ledgerflow")
        == "postgresql+psycopg://ledgerflow:secret@db.internal/ledgerflow"
    )
    assert normalize_database_url("sqlite:///./local.db") == "sqlite:///./local.db"


def test_configured_web_origin_receives_cors_headers(monkeypatch) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://ledgerflow.example.com,http://localhost:8080",
    )
    client = TestClient(create_app())

    response = client.options(
        "/api/v1/charge-management/components",
        headers={
            "Origin": "https://ledgerflow.example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://ledgerflow.example.com"
    assert "authorization" in response.headers["access-control-allow-headers"].lower()
