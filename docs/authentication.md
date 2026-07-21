# Authentication And Authorization

## Recommended Boundary

The API validates JWTs itself, while the deploying system remains the identity provider. This gives the module a safe default and lets it run behind an API gateway without trusting unsigned identity headers.

JWT mode is the default. Every charge-management endpoint requires a bearer token.

## JWKS Configuration

Asymmetric signing through JWKS is recommended for production:

```text
AUTH_MODE=jwt
JWT_ISSUER=https://identity.example.com/
JWT_AUDIENCE=charge-management-api
JWT_JWKS_URL=https://identity.example.com/.well-known/jwks.json
JWT_ALGORITHMS=RS256
JWT_ROLES_CLAIM=roles
JWT_TENANT_CLAIM=tenant_id
JWT_LEEWAY_SECONDS=30
```

The validator requires `exp` and `sub`, verifies signature, issuer, and audience, and rejects missing or invalid configuration. `JWT_AUDIENCE` and `JWT_ALGORITHMS` accept comma-separated values. JWKS signing keys are cached by the PyJWT client.

Claim paths may be dotted. For example, `JWT_ROLES_CLAIM=realm_access.roles` reads roles from:

```json
{
  "realm_access": {
    "roles": ["charge-reader", "rate-manager"]
  }
}
```

Role claims may be arrays or comma/space-separated strings. Tenant claims are optional at authentication time because not every deployment is multi-tenant; authorization policy should require them when tenant isolation is needed.

## Shared-Secret Configuration

HS256 is supported for controlled deployments:

```text
AUTH_MODE=jwt
JWT_ISSUER=https://identity.example.com/
JWT_AUDIENCE=charge-management-api
JWT_ALGORITHMS=HS256
JWT_SHARED_SECRET=<read from a secret manager>
```

Do not put the shared secret in Git, a container image, or command history. Prefer asymmetric keys when multiple services validate tokens.

## Development Mode

```text
AUTH_MODE=development
```

Development mode requires a non-empty bearer token but does not validate it. It optionally reads `X-Subject`, `X-Roles`, and `X-Tenant-Id` for local tests. It must never be used in a shared, staging, or production environment.

## Authorization

Authentication answers who called. `PolicyAdapter` answers whether that principal may perform an action on a scope. Every route invokes an action key such as `charge.fx_rates.create` or `charge.allocation_profiles.read`.

The included `DefaultPolicyAdapter` only rejects a missing principal. It is not a production RBAC or tenant-isolation policy. Integrators should replace it with a policy adapter that:

- Maps role claims to action keys.
- Enforces tenant, company, customer, vendor, or other row scope.
- Applies the same scope to read and write paths.
- Fails closed when policy data is unavailable.
- Emits audit data without logging raw tokens.

An upstream gateway can perform an additional JWT check, but the API should still validate the token unless network and workload identity controls make that trust boundary explicit and a custom authentication adapter is introduced.
