from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from app.db.url import normalize_database_url
from app.main import app, create_app
from app.operations.readiness import DatabaseReadinessError, check_database_readiness


def test_health_endpoint_is_available_without_authentication() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint_reports_database_ok(monkeypatch) -> None:
    called = False

    def stub_readiness() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr("app.main.readiness.check_database_readiness", stub_readiness)

    response = TestClient(app).get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok"}}
    assert called is True


def test_readiness_endpoint_returns_service_unavailable_on_database_failure(monkeypatch) -> None:
    def failing_readiness() -> None:
        raise DatabaseReadinessError("Database connectivity check failed.")

    monkeypatch.setattr("app.main.readiness.check_database_readiness", failing_readiness)

    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "unavailable"},
    }


def test_database_readiness_check_succeeds_for_live_engine() -> None:
    check_database_readiness(create_engine("sqlite://"))


def test_database_readiness_check_raises_for_connection_errors(monkeypatch) -> None:
    target_engine = create_engine("sqlite://")

    def broken_connect():
        raise SQLAlchemyError("boom")

    monkeypatch.setattr(target_engine, "connect", broken_connect)

    try:
        check_database_readiness(target_engine)
    except DatabaseReadinessError as exc:
        assert str(exc) == "Database connectivity check failed."
    else:
        raise AssertionError("Expected DatabaseReadinessError")


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
