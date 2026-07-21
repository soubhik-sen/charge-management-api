from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from typing import Any, Protocol

from fastapi import Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt import InvalidTokenError, PyJWKClient


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: tuple[str, ...] = ()
    tenant_id: str | None = None


class PolicyAdapter(Protocol):
    def assert_allowed(self, principal: Principal, action: str, scope: dict[str, int | None]) -> None:
        """Raise when the principal is not allowed to perform the action."""


class FinancialExportAdapter(Protocol):
    def post_export(self, payload: dict) -> dict:
        """Send export payload to the consuming product or ledger integration."""


class SourceObjectHydrator(Protocol):
    def hydrate(self, source_object_type: str, source_object_id: str) -> dict:
        """Hydrate PO/SO/shipment/container or any consuming-app source object."""


class DefaultPolicyAdapter:
    def assert_allowed(self, principal: Principal, action: str, scope: dict[str, int | None]) -> None:
        if not principal.subject:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


bearer_scheme = HTTPBearer(
    auto_error=False,
    description="A JWT issued for this API, or any non-empty token in explicit development mode.",
)


def require_bearer_principal(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    x_subject: str | None = Header(default=None, alias="X-Subject"),
    x_roles: str | None = Header(default=None, alias="X-Roles"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
) -> Principal:
    token = _bearer_token(credentials)
    mode = os.getenv("AUTH_MODE", "jwt").strip().lower()
    if mode == "development":
        subject = (x_subject or "api-user").strip() or "api-user"
        roles = tuple(role.strip() for role in (x_roles or "").split(",") if role.strip())
        tenant_id = (x_tenant_id or "").strip() or None
        return Principal(subject=subject, roles=roles, tenant_id=tenant_id)
    if mode != "jwt":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unsupported AUTH_MODE configuration.",
        )

    claims = _decode_jwt(token)
    subject = str(claims.get("sub") or "").strip()
    if not subject:
        raise _authentication_error("JWT subject claim is required.")
    roles = _roles_from_claim(_claim_value(claims, os.getenv("JWT_ROLES_CLAIM", "roles")))
    tenant_value = _claim_value(claims, os.getenv("JWT_TENANT_CLAIM", "tenant_id"))
    tenant_id = str(tenant_value).strip() if tenant_value is not None else None
    return Principal(subject=subject, roles=roles, tenant_id=tenant_id or None)


def _bearer_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _authentication_error("Bearer token required.")
    token = credentials.credentials.strip()
    if not token:
        raise _authentication_error("Bearer token required.")
    return token


def _decode_jwt(token: str) -> dict[str, Any]:
    issuer = os.getenv("JWT_ISSUER", "").strip()
    audience_value = os.getenv("JWT_AUDIENCE", "").strip()
    algorithms = [
        value.strip()
        for value in os.getenv("JWT_ALGORITHMS", "RS256").split(",")
        if value.strip()
    ]
    if not issuer or not audience_value or not algorithms:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT_ISSUER, JWT_AUDIENCE, and JWT_ALGORITHMS must be configured.",
        )

    jwks_url = os.getenv("JWT_JWKS_URL", "").strip()
    shared_secret = os.getenv("JWT_SHARED_SECRET", "")
    if jwks_url:
        try:
            verification_key = _jwk_client(jwks_url).get_signing_key_from_jwt(token).key
        except Exception as exc:
            raise _authentication_error("JWT signing key could not be resolved.") from exc
    elif shared_secret:
        verification_key = shared_secret
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configure JWT_JWKS_URL or JWT_SHARED_SECRET.",
        )

    audience: str | list[str]
    audience_values = [value.strip() for value in audience_value.split(",") if value.strip()]
    audience = audience_values[0] if len(audience_values) == 1 else audience_values
    try:
        return jwt.decode(
            token,
            verification_key,
            algorithms=algorithms,
            audience=audience,
            issuer=issuer,
            leeway=int(os.getenv("JWT_LEEWAY_SECONDS", "30")),
            options={"require": ["exp", "sub"]},
        )
    except (InvalidTokenError, ValueError) as exc:
        raise _authentication_error("JWT validation failed.") from exc


@lru_cache(maxsize=8)
def _jwk_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url, cache_keys=True)


def _claim_value(claims: dict[str, Any], path: str) -> Any:
    value: Any = claims
    for part in (item for item in path.split(".") if item):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _roles_from_claim(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        candidates = value.replace(",", " ").split()
    elif isinstance(value, (list, tuple, set)):
        candidates = [str(item) for item in value]
    else:
        candidates = []
    return tuple(role.strip() for role in candidates if role.strip())


def _authentication_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
