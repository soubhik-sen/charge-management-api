# Charge Management API

Standalone, reusable Charge Management API for logistics-grade pricing, quote comparison, charge-document lifecycle, invoice matching, and export-ready financial output.

This repo is intentionally independent from FLUXPORT. FLUXPORT owns its embedded implementation locally; this project keeps an adapter-neutral API and domain boundary that can later be reused by other products.

## Scope
- Generic terminology only: charge components, payer/payee contracts, rate books, calculation templates, quote requests, quote offers, quote options, charge documents, invoices, match results, and export batches.
- Adapter-neutral quotation policy supports `REQUIRED`, `OPTIONAL`, and `DIRECT_ONLY` setup without FLUXPORT-specific administration assumptions.
- Adapter-neutral quote acceptance supports `CUSTOMER_ACCEPTANCE` and `AUTO_ACCEPT`. `provider_cost_layer_enabled` controls whether rating requires provider-cost contracts or can rate customer-facing options from customer-pricing contracts only.
- Quote requests include neutral RFQ cargo fields for ocean and air/package scenarios: `container_count`, `package_count`, `package_type`, optional weight/volume fields, and `valid_from` / `valid_to` validity windows for later commitment consumption.
- Rate books are durable API objects: consuming applications can create, list/search, open workspace detail, and update rate entries without keeping transient response IDs.
- Calculation templates are durable API objects: consuming applications can create, list/search, open workspace detail, and update ordered component steps with optional rate-book references.
- Charge component aliases are durable API objects for mapping external proposal or invoice labels to system charge components with default basis, level, staged allocation drivers, `final_posting_level`, quantity UOM, and optional customer/forwarder/transport-mode scope.
- Charge allocation profiles are versioned API objects. Profile versions use the canonical fields `source_level`, `source_to_house_driver`, `house_to_item_driver`, and `final_posting_level`; alias overrides use `INHERIT_PROFILE`, `OVERRIDE_PROFILE`, and `NO_ALLOCATION`.
- Business date profiles are versioned API objects for adapter-neutral exchange-rate date fallback chains. Assignments are explicit per owner, `shipment_scope` (`OCEAN_HOUSE` or `AIR_HOUSE`), and `business_purpose`; only one profile can own an effective assignment slot. Components can either keep legacy `charge_date_basis`, inherit the exact shipment-scope assignment, or override with a published profile directly.
- Charge components include adapter-neutral `charge_date_basis` metadata so consuming applications can persist a document-date choice without embedding host-specific shipment resolution logic.
- Charge documents carry an optional neutral `shipment_scope`. Charge lines can override `charge_date_basis`; date resolution precedence is explicit `exchange_rate_date`, explicit manual `charge_date`, line `charge_date_basis`, component profile/legacy policy, then document fallback.
- Contracts can store default rate book/default calculation template references on the header; lines can override them for specific lane/component rules. Release requires at least one line and a header or line rate source.
- Quote requests are durable workbench objects, not create-only actions: the API exposes list and workspace endpoints so consuming applications can search, reopen, submit a draft RFQ to `REQUESTED`, continue rating/ranking, and inspect linked offers, options, commitments, and charge documents.
- Quote awards create neutral quote commitments that can be matched and consumed by later execution objects without assuming a specific host application's shipment model.
- Charge invoices are durable objects: the API exposes list/search and workspace endpoints so consuming applications can reopen captured invoices, inspect related charge documents, and continue invoice matching after refresh.
- Charge document lines can store calculation audit JSON so consuming applications can explain allocated amounts without coupling to a host application's shipment model.
- No FLUXPORT runtime dependency.
- No SAP object names in implementation-facing terminology.
- Extension seams exist for auth, policy, source-object hydration, financial export, and document storage.

## Setup And Run

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\uvicorn app.main:app --reload
```

OpenAPI will be available at:

```text
http://127.0.0.1:8000/openapi.json
```

Detailed DB-backed setup instructions are in [docs/setup.md](docs/setup.md).

## Database
Alembic is configured in this repo. Migrations create charge settings, components, rate books, contracts, calculation templates, quote requests, quote offers, quote options, quote commitments, charge documents, invoices, match results, and export batches. They also seed 32 common charge components.

Set `DATABASE_URL` before running migrations or the API. PostgreSQL is the target runtime database; SQLite is only suitable for local smoke tests.

## Contract Alignment
The endpoint shape mirrors the embedded FLUXPORT charge module:

- `GET /api/v1/charge-management/initialization-data`
- `GET /api/v1/charge-management/component-aliases`
- `POST /api/v1/charge-management/component-aliases`
- `PUT|DELETE /api/v1/charge-management/component-aliases/{id}`
- `GET|POST /api/v1/charge-management/business-date-profiles`
- `GET|PUT /api/v1/charge-management/business-date-profiles/{id}`
- `POST /api/v1/charge-management/business-date-profiles/{id}/versions`
- `PUT /api/v1/charge-management/business-date-profile-versions/{version_id}`
- `POST /api/v1/charge-management/business-date-profile-versions/{version_id}/publish`
- `GET|POST /api/v1/charge-management/business-date-profiles/{id}/assignments`
- `PUT|DELETE /api/v1/charge-management/business-date-profile-assignments/{assignment_id}`
- `GET /api/v1/charge-management/rate-books`
- `POST /api/v1/charge-management/rate-books`
- `GET|PUT /api/v1/charge-management/rate-books/{id}/workspace`
- `GET /api/v1/charge-management/calculation-templates`
- `POST /api/v1/charge-management/calculation-templates`
- `GET|PUT /api/v1/charge-management/calculation-templates/{id}/workspace`
- `GET /api/v1/charge-management/contracts`
- `GET /api/v1/charge-management/quote-requests`
- `POST /api/v1/charge-management/quote-requests`
- `GET /api/v1/charge-management/quote-requests/{id}/workspace`
- `POST /api/v1/charge-management/quote-requests/{id}/offers`
- `POST /api/v1/charge-management/quote-requests/{id}/determine-contracts`
- `POST /api/v1/charge-management/quote-requests/{id}/rate`
- `POST /api/v1/charge-management/quote-requests/{id}/rank`
- `POST /api/v1/charge-management/quote-requests/{id}/award`
- `POST /api/v1/charge-management/quote-commitments/match`
- `POST /api/v1/charge-management/quote-commitments/{id}/consume`
- `POST /api/v1/charge-management/quote-commitment-consumptions/{id}/reverse`
- `GET /api/v1/charge-management/charge-documents`
- `POST /api/v1/charge-management/charge-documents`
- `DELETE /api/v1/charge-management/charge-documents/{id}`
- `GET|PUT /api/v1/charge-management/contracts/{id}/workspace`
- `POST /api/v1/charge-management/contracts/{id}/release`
- `GET|PUT /api/v1/charge-management/charge-documents/{id}/workspace`
- `GET /api/v1/charge-management/invoices`
- `POST /api/v1/charge-management/invoices`
- `GET /api/v1/charge-management/invoices/{id}/workspace`
- `POST /api/v1/charge-management/invoices/{id}/match`
- `POST /api/v1/charge-management/charge-documents/{id}/approve`
- `POST /api/v1/charge-management/charge-documents/{id}/post-export`
- `POST /api/v1/charge-management/charge-documents/{id}/reverse`

Additional standalone management endpoints are included for creating `rate-books`, `calculation-templates`, and `contracts` while the admin UI is not yet built.

Business-date assignment list endpoints accept `shipment_scope` and `business_purpose` filters. Assignment uniqueness is evaluated across profiles using owner scope plus those dimensions, preventing ambiguous effective profile selection.

The standalone contract keeps `HOUSE` target support on charge lines and final posting levels, and it preserves the generic staged-driver naming used by the canonical FLUXPORT charge allocation profile contract.
