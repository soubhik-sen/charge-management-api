from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.url import normalize_database_url
from app.main import app


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
