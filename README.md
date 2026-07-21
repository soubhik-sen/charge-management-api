# Charge Management API

An open-source, adapter-neutral API for defining, calculating, allocating, converting, approving, and reconciling charges. It is designed for logistics and other multi-party pricing workflows without requiring a particular ERP, identity provider, or host application.

> **Project status:** `0.2.0` beta. The API and database are usable, but compatibility may still change before `1.0.0`.

## Why This Project

Charge calculation rarely stops at `quantity * rate`. Real implementations also need versioned rate sources, payer/payee contracts, date selection, currency conversion, allocation, quote comparison, approval, invoice matching, persistence, and an audit trail. This project keeps those concerns in one reusable service while leaving product-specific UI, source-object models, authorization policy, and financial posting behind adapters.

## Capabilities

- Persistent charge components, aliases, rate books, calculation templates, and contracts.
- Versioned allocation profiles with shipment, container, house, and item-level drivers.
- Versioned business-date profiles with ordered fallback steps and scoped assignments.
- FX source/rate maintenance plus exact-date, prior-date, direct, and inverse resolution.
- Quote request, offer, rating, ranking, award, commitment, and consumption lifecycle.
- Charge documents, calculation audit data, approval, reversal, and export lifecycle.
- Invoice capture, workspace persistence, and matching.
- PostgreSQL runtime with SQLAlchemy and Alembic migrations.
- JWT authentication using any standards-compliant issuer through JWKS or a shared secret.
- Generated OpenAPI contract and PostgreSQL-backed API tests with JUnit/coverage reports.

## Five-Minute Start

Prerequisites: Docker with Compose.

```bash
git clone https://github.com/soubhik-sen/charge-management-api.git
cd charge-management-api
docker compose up --build
```

The local compose profile starts PostgreSQL, applies migrations, and exposes:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI: `http://localhost:8000/openapi.json`

Verify the API:

```bash
curl -H "Authorization: Bearer local-dev-token" \
  http://localhost:8000/api/v1/charge-management/initialization-data
```

The compose profile deliberately uses `AUTH_MODE=development` for evaluation. It still requires a bearer token, but it does not verify the token. Configure JWT mode before exposing the API to any network.

## Authentication Decision

JWT validation is built in and secure by default. That prevents a reusable financial API from becoming accidentally anonymous while avoiding ownership of users, passwords, or sessions.

The deploying application supplies its own issuer, audience, and JWKS URL. The API validates token signature, issuer, audience, expiry, and subject, then maps configurable role and tenant claims to a neutral `Principal`. Fine-grained authorization and tenant scope remain the responsibility of the replaceable `PolicyAdapter`.

See [Authentication](docs/authentication.md) for production configuration and gateway integration.

## Native Python Start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

On Windows PowerShell, activate with `.\.venv\Scripts\Activate.ps1` instead. Set `DATABASE_URL` and authentication variables in the process environment before migration or startup. PostgreSQL is the supported runtime database; SQLite is intended only for local smoke tests. See [Setup](docs/setup.md).

## Documentation

| Guide | Purpose |
| --- | --- |
| [Quickstart](docs/quickstart.md) | First local call with Docker or Python |
| [Core concepts](docs/core-concepts.md) | What each module means and how the modules work together |
| [API examples](docs/api-examples.md) | Allocation, business-date, and FX requests |
| [Authentication](docs/authentication.md) | JWT, claims, local mode, and authorization boundary |
| [Database](docs/database.md) | Schema groups, migrations, and persistence behavior |
| [Testing](docs/testing.md) | Local and CI reports, PostgreSQL tests, and OpenAPI checks |
| [Architecture](docs/architecture.md) | Layers, domain boundary, and extension adapters |
| [Generated OpenAPI](app/contracts/charge-management-api.openapi.json) | Complete machine-readable endpoint contract |

## Test Results

Run:

```bash
python scripts/run_tests.py
```

The command writes `test-results/summary.md`, `junit.xml`, and `coverage.xml`. GitHub Actions runs the same API suite against PostgreSQL on Python 3.11, 3.12, and 3.13 and retains each report bundle as a workflow artifact. Generated local reports are intentionally not committed.

## Project Boundary

The service owns generic charge-management API contracts, database schemas, migrations, rating behavior, and lifecycle behavior. Integrators own product UI, identity issuance, authorization rules, tenant isolation policy, source-object hydration, document storage, and ERP/ledger export implementations.

## Contributing And Security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md), not through public issues.

Licensed under the [Apache License 2.0](LICENSE).
