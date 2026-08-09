# LedgerFlow Web Application

The Flutter web application under `apps/ledgerflow_web` is the reference user interface for the LedgerFlow API. It is part of this monorepo and has no dependency on FLUX or another host application.

## Workspaces

| Workspace | Purpose |
| --- | --- |
| Overview | Operational KPIs, charge volume and margin trend, approval queue, and recent charge documents. |
| Quotes | Quote request context, lifecycle, ranked commercial options, matched contracts, and payer/payee charge-line comparison. |
| Charge documents | Expected charges, status, approval checks, and calculation, allocation, business-date, rate, and FX provenance. |
| Invoices | Exception-first line matching, variance totals, resolution choices, match health, and linked document context. |
| Rate books | Version/status context, date-effective rate rows, applicability, calculation/allocation profile references, and selected-rate inspection. |
| Components | Search, inspect, create, edit, deactivate, and attach calculation, allocation, and business-date defaults. |
| Profiles | Create/edit calculation and allocation profiles, manage draft versions, publish releases, and inspect usage. |
| FX & dates | Inspect directional FX rates; create/version/publish business-date profiles and maintain scoped assignments. |

The UI fields use the public JSON names from the OpenAPI contract. Unknown optional fields degrade to empty or inherited values instead of requiring host-specific metadata.

## Demo And Live Modes

The application opens in demo mode with representative records. This makes the repository immediately reviewable without weakening API security or preloading a shared database with public credentials.

Select **Connect API** to enter:

- The API base URL.
- A bearer access token issued for that API.

The token is kept only in the running application state. It is not written to local storage, logs, source code, or build configuration. Refreshing the page clears it.

The UI never receives the JWT signing secret. Production deployments should use an external OIDC/OAuth issuer with asymmetric signing and configure the API through `JWT_ISSUER`, `JWT_AUDIENCE`, `JWT_JWKS_URL`, and `JWT_ALGORITHMS`.

## Local Development

Start the API first, then run:

```bash
cd apps/ledgerflow_web
flutter pub get
flutter run -d chrome --dart-define=LEDGERFLOW_API_URL=http://localhost:8000
```

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

The compiled site is written to `apps/ledgerflow_web/build/web`. Configure an SPA rewrite from `/*` to `/index.html` on the static host.

## Administration Workflows

When connected to a live API, the reference UI performs persisted component and profile administration through the public REST contract. It supports component create/edit/deactivate, calculation and allocation profile create/edit/version/publish, business-date profile create/edit/version/publish, and business-date assignment create/edit/remove.

Demo mode deliberately disables writes. Profile selectors show published definitions only, while inspectors retain complete version history. API lifecycle and authorization checks remain authoritative.

See [UI administration](ui-administration.md) for task-oriented instructions. Other API lifecycle operations, including rate-book workspace replacement, quote award, charge approval/reversal/export, and invoice matching, remain documented in [API examples](api-examples.md) and interactive Swagger at `/docs` until their reference UI actions are implemented.
