from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
import jwt

from app.api.v1 import charge_management
from app.main import app


client = TestClient(app)


def test_jwt_authentication_uses_verified_claims(monkeypatch) -> None:
    class CapturingPolicy:
        principal = None

        def assert_allowed(self, principal, _action, _scope) -> None:
            self.principal = principal

    capturing_policy = CapturingPolicy()
    monkeypatch.setattr(charge_management, "policy", capturing_policy)
    secret = "test-only-shared-secret-with-sufficient-length"
    monkeypatch.setenv("AUTH_MODE", "jwt")
    monkeypatch.setenv("JWT_ISSUER", "https://issuer.example.test")
    monkeypatch.setenv("JWT_AUDIENCE", "charge-management-api")
    monkeypatch.setenv("JWT_ALGORITHMS", "HS256")
    monkeypatch.setenv("JWT_SHARED_SECRET", secret)
    token = jwt.encode(
        {
            "sub": "jwt-user",
            "roles": ["RATE_MANAGER"],
            "tenant_id": "tenant-1",
            "iss": "https://issuer.example.test",
            "aud": "charge-management-api",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )

    response = client.get(
        "/api/v1/charge-management/initialization-data",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Subject": "spoofed-header-user",
        },
    )

    assert response.status_code == 200, response.text
    assert capturing_policy.principal.subject == "jwt-user"
    assert capturing_policy.principal.roles == ("RATE_MANAGER",)
    assert capturing_policy.principal.tenant_id == "tenant-1"


def test_jwt_authentication_rejects_wrong_audience(monkeypatch) -> None:
    secret = "test-only-shared-secret-with-sufficient-length"
    monkeypatch.setenv("AUTH_MODE", "jwt")
    monkeypatch.setenv("JWT_ISSUER", "https://issuer.example.test")
    monkeypatch.setenv("JWT_AUDIENCE", "charge-management-api")
    monkeypatch.setenv("JWT_ALGORITHMS", "HS256")
    monkeypatch.setenv("JWT_SHARED_SECRET", secret)
    token = jwt.encode(
        {
            "sub": "jwt-user",
            "iss": "https://issuer.example.test",
            "aud": "different-api",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )

    response = client.get(
        "/api/v1/charge-management/initialization-data",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_jwt_mode_fails_closed_when_verification_is_not_configured(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "jwt")
    monkeypatch.delenv("JWT_ISSUER", raising=False)
    monkeypatch.delenv("JWT_AUDIENCE", raising=False)
    monkeypatch.delenv("JWT_JWKS_URL", raising=False)
    monkeypatch.delenv("JWT_SHARED_SECRET", raising=False)

    response = client.get(
        "/api/v1/charge-management/initialization-data",
        headers={"Authorization": "Bearer opaque-token"},
    )

    assert response.status_code == 503


def test_openapi_declares_bearer_authentication() -> None:
    schema = client.get("/openapi.json").json()

    bearer = schema["components"]["securitySchemes"]["HTTPBearer"]
    assert bearer["type"] == "http"
    assert bearer["scheme"] == "bearer"
    for path_item in schema["paths"].values():
        for operation in path_item.values():
            if isinstance(operation, dict) and "responses" in operation:
                assert {"HTTPBearer": []} in operation["security"]
