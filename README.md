# LedgerFlow

[![CI](https://github.com/soubhik-sen/charge-management-api/actions/workflows/ci.yml/badge.svg)](https://github.com/soubhik-sen/charge-management-api/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

An open-source charge-management monorepo for defining, calculating, allocating, converting, approving, and reconciling charges. LedgerFlow includes an adapter-neutral FastAPI service, PostgreSQL schema and migrations, and a responsive Flutter web workspace without requiring a particular ERP or identity provider.

> **Project status:** `0.2.0` beta. The API and database are usable, but compatibility may still change before `1.0.0`.

## Why This Project

Charge calculation rarely stops at `quantity * rate`. Real implementations also need versioned rate sources, payer/payee contracts, date selection, currency conversion, allocation, quote comparison, approval, invoice matching, persistence, and an audit trail. This project keeps those concerns in one reusable service while leaving product-specific UI, source-object models, authorization policy, and financial posting behind adapters.

## Capabilities

- Effective-dated charge components, aliases, versioned rate books, executable calculation templates, and party-bound contracts with header templates, conditional routes, and deterministic selection.
- Deterministic rate-row selection by applicability, specificity, priority, and scale floor.
- Versioned calculation profiles for flat, single-axis, and compound rate formulas.
- Seeded road-freight pack with FTL/LTL, fuel, toll, waiting, ADR, pallet, stop, delivery, permit, CMR, calculation, allocation, and date-policy metadata.
- A side-effect-free calculation preview API for flat, quantity, percentage, profile, FX, and allocation evaluation.
- Versioned allocation profiles with effective periods, missing-driver policy, and exact minor-unit distribution.
- Versioned business-date profiles with effective periods, ordered fallback steps, scoped assignments, and standalone resolution.
- FX source/rate maintenance plus exact-date, prior-date, direct, and inverse resolution.
- Quote request, offer, rating, ranking, award, commitment, and consumption lifecycle.
- Charge documents, calculation audit data, approval, reversal, and export lifecycle.
- Invoice capture, workspace persistence, and posting-line-aware component matching.
- PostgreSQL runtime with SQLAlchemy and Alembic migrations.
- JWT authentication using any standards-compliant issuer through JWKS or a shared secret.
- Generated OpenAPI contract and PostgreSQL-backed API tests with JUnit/coverage reports.
- Responsive operations UI for contract authoring and release; quote JSON import, matching, rating, ranking, award, and provenance; charge-document approval, export, reversal, guarded deletion, and audit snapshots; invoice reconciliation and guarded deletion; component-scoped rate books; calculation templates; components; profiles; business dates; and FX rates.
- Opt-in [road pricing study](docs/road-pricing-study.md) with realistic component-specific rate tables, subtotal-derived fuel, conditional accessorials, and a statistical benchmark.

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

Run the web workspace in a second terminal:

```bash
cd apps/ledgerflow_web
flutter pub get
flutter run -d chrome --dart-define=LEDGERFLOW_API_URL=http://localhost:8000
```

The UI opens in an empty disconnected state and never presents sample records as live data. Select **Connect API**, enter the API URL (the current browser origin is used by default when no build-time URL is configured), and use `local-dev-token` for the Docker development profile. The token is held only in application memory.

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

## Deploy To Render

The repository includes `render.yaml` for the `LEDGERFLOW` project's `Dev & QA` environment. The Blueprint provisions:

- `ledgerflow-api-devqa`, a Python web service that applies Alembic migrations before startup.
- `ledgerflow-web-devqa`, a static Flutter web application with demo and live API modes.
- `ledgerflow-db-devqa`, a private Render PostgreSQL database.
- Secure JWT validation with a Render-generated HS256 secret.

Create or update the Blueprint from this repository in Render. The API exposes `/health` for liveness and `/ready` for database-backed readiness, Swagger UI is `/docs`, and all charge-management operations remain protected by bearer authentication. Retrieve the generated JWT secret only through Render's secret controls when minting Dev & QA tokens; never commit it.

## Documentation

| Guide | Purpose |
| --- | --- |
| [Quickstart](docs/quickstart.md) | First local call with Docker or Python |
| [Core concepts](docs/core-concepts.md) | What each module means and how the modules work together |
| [Caller attribute mapping](docs/caller-attribute-mapping.md) | Canonical rate dimensions, per-caller schema mappings, and lifecycle rules |
| [Road freight metadata](docs/road-freight-metadata.md) | Seeded road components, profiles, caller inputs, and standards basis |
| [Road pricing study](docs/road-pricing-study.md) | Rerunnable contract, calculation template, rate tables, and expected quote result |
| [API examples](docs/api-examples.md) | Calculation preview, allocation, business-date, FX, and rating requests |
| [Authentication](docs/authentication.md) | JWT, claims, local mode, and authorization boundary |
| [Database](docs/database.md) | Schema groups, migrations, and persistence behavior |
| [Testing](docs/testing.md) | Local and CI reports, PostgreSQL tests, and OpenAPI checks |
| [Architecture](docs/architecture.md) | Layers, domain boundary, and extension adapters |
| [Web application](docs/web-application.md) | UI modules, local use, authentication, and deployment |
| [UI administration](docs/ui-administration.md) | Create, publish, assign, and use components and profiles |
| [Road quote fixture](examples/road-quote-request.json) | Importable caller request for an end-to-end road quote test |
| [Generated OpenAPI](app/contracts/charge-management-api.openapi.json) | Complete machine-readable endpoint contract |

## Test Results

Run:

```bash
python scripts/run_tests.py
```

The command writes `test-results/summary.md`, `junit.xml`, and `coverage.xml`. GitHub Actions runs the same API suite against PostgreSQL on Python 3.11, 3.12, and 3.13 and retains each report bundle as a workflow artifact. Generated local reports are intentionally not committed.

## Project Boundary

The monorepo owns generic charge-management API contracts, database schemas, migrations, rating behavior, lifecycle behavior, and an optional reference UI. Integrators still own identity issuance, authorization rules, tenant isolation policy, source-object hydration, document storage, and ERP/ledger export implementations. The Flutter UI is an API client, not a privileged security boundary.

## Contributing And Security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md), not through public issues.

Licensed under the [Apache License 2.0](LICENSE).
