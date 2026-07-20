from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fastapi import Header, HTTPException, status


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


def require_bearer_principal(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_subject: str | None = Header(default=None, alias="X-Subject"),
    x_roles: str | None = Header(default=None, alias="X-Roles"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
) -> Principal:
    token = (authorization or "").strip()
    if not token.lower().startswith("bearer ") or not token[7:].strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    subject = (x_subject or "api-user").strip() or "api-user"
    roles = tuple(role.strip() for role in (x_roles or "").split(",") if role.strip())
    return Principal(subject=subject, roles=roles, tenant_id=x_tenant_id)
