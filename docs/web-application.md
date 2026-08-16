# LedgerFlow Web Application

The Flutter web application under `apps/ledgerflow_web` is the reference user interface for the LedgerFlow API. It is part of this monorepo and has no dependency on FLUX or another host application.

## Workspaces

| Workspace | Purpose |
| --- | --- |
| Overview | Operational KPIs, charge volume and margin trend, approval queue, and recent charge documents. |
| Quotes | Search, filter, and page through quote requests; create or import requests, determine matching contracts, rate and rank options, award a winner, and inspect exact charge-line provenance. |
| Contracts | Create party-bound payer/payee contracts, configure applicability and pricing on contract lines, and release contracts for quote matching. |
| Charge documents | Search, filter, and page through documents; inspect expected/actual/approved amounts and exact provenance, change mutable status, refresh authoritative approval checks, approve, export, and reverse. |
| Invoices | Search, filter, and page through invoices; use exception-first line matching, variance totals, resolution choices, match health, and linked document context. |
| Rate books | Search, filter, and page through versioned book families; create books, edit drafts, create/publish versions, inspect real version history, and maintain date-effective rate rows and profile references. |
| Calculation templates | Build ordered multi-component calculations, select component-specific books, and manage immutable published versions. |
| Components | Search, inspect, create, edit, deactivate, and attach calculation, allocation, and business-date defaults. |
| Profiles | Create/edit calculation and allocation profiles, manage draft versions, publish releases, and inspect usage. |
| FX & dates | Create/edit/deactivate directional FX rates; create/version/publish effective-dated business-date profiles and maintain scoped assignments. |
| Caller mappings | Maintain canonical pricing dimensions and versioned per-caller schema mappings; preview raw caller payload normalization before integration. |

The UI fields use the public JSON names from the OpenAPI contract. Unknown optional fields degrade to empty or inherited values instead of requiring host-specific metadata.

## Demo And Live Modes

The application opens in demo mode with representative records. This makes the repository immediately reviewable without weakening API security or preloading a shared database with public credentials.

Select **Connect API** to enter:

- The API base URL.
- A bearer access token issued for that API.

Tokens entered through **Connect API** are kept only in the running application state. They are not written to local storage or logs, and refreshing the page clears them.

For local testing only, `LEDGERFLOW_API_TOKEN` can be supplied as a Dart build define. The application connects automatically when this value is present. Dart defines are embedded in the compiled web assets, so never use this mechanism for production credentials.

The UI never receives the JWT signing secret. Production deployments should use an external OIDC/OAuth issuer with asymmetric signing and configure the API through `JWT_ISSUER`, `JWT_AUDIENCE`, `JWT_JWKS_URL`, and `JWT_ALGORITHMS`.

## Local Development

Start the API first, then run:

```bash
cd apps/ledgerflow_web
flutter pub get
flutter run -d chrome --web-port=8080 \
  --dart-define=LEDGERFLOW_API_URL=http://localhost:8000 \
  --dart-define=LEDGERFLOW_API_TOKEN=local-dev-token \
  --dart-define=LEDGERFLOW_UI_SCALE=1.0
```

`LEDGERFLOW_UI_SCALE` defaults to `1.0`, the normal Flutter logical size. Set a lower value only when an embedding host intentionally requires a denser interface.

Allow the Flutter development origin in the API process:

```text
CORS_ALLOWED_ORIGINS=http://localhost:8080
```

If Flutter selects a different port, pass `--web-port=8080` or update the origin. CORS values are exact, comma-separated origins; do not include path segments.

## Build

```bash
cd apps/ledgerflow_web
flutter analyze
flutter test
flutter build web --release --dart-define=LEDGERFLOW_API_URL=https://api.example.com
```

Production builds intentionally omit `LEDGERFLOW_API_TOKEN` and obtain a user token through **Connect API** or a host application's identity flow.

The compiled site is written to `apps/ledgerflow_web/build/web`. Configure an SPA rewrite from `/*` to `/index.html` on the static host.

For local same-origin operation, set `LEDGERFLOW_WEB_DIRECTORY=apps/ledgerflow_web/build/web` on the API process and build with an empty `LEDGERFLOW_API_URL`. The client then uses relative `/api`, `/health`, and `/docs` routes, avoiding CORS and host-name mismatches. API, health, and documentation routes remain registered ahead of the optional static mount.

## Administration Workflows

When connected to a live API, the reference UI performs persisted master-data and transaction administration through the public REST contract. It supports component create/edit/deactivate; calculation, allocation, and business-date profile create/edit/version/publish; business-date assignment create/edit/remove; rate-book create/draft-edit/version/publish; canonical pricing-dimension and caller-mapping maintenance; calculation-template maintenance; FX-rate create/edit/deactivate; contract create/edit/release; quote create/import/submit/determine/rate/rank/award; charge-document status/approval/export/reversal/delete; and guarded invoice deletion. Contracts support a row-free header template, component-free conditional template routes, explicit selection priority, and legacy direct component lines.

Demo mode deliberately disables writes. Profile selectors show published definitions only, while inspectors retain complete version history. API lifecycle and authorization checks remain authoritative.

See [UI administration](ui-administration.md) for task-oriented instructions. Invoice capture, workspace editing, and matching remain documented in [API examples](api-examples.md) and interactive Swagger at `/docs`; the reference UI currently exposes invoice inspection and guarded deletion.
