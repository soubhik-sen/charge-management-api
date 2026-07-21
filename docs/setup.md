# Setup And Run Manual

This manual sets up the standalone Charge Management API as a DB-backed service.

## 1. Prerequisites
- Python 3.11 or newer.
- PostgreSQL 14 or newer for normal development/deployment.
- PowerShell on Windows.

SQLite can be used for local smoke tests, but PostgreSQL should be used for real development because production integrations will depend on transactional behavior and database-level constraints.

## 2. Create Environment

```powershell
cd C:\CW\charge-management-api
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -e ".[dev]"
```

## 3. Configure Database

Set `DATABASE_URL` before running Alembic or the API.

PostgreSQL example:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://charge_user:charge_password@localhost:5432/charge_management"
```

Local SQLite smoke-test example:

```powershell
$env:DATABASE_URL = "sqlite:///./charge_management.db"
```

Do not commit real passwords or connection strings.

## 4. Apply Migrations

```powershell
.\.venv\Scripts\alembic.exe upgrade head
```

The migration set creates the full charge domain schema, including quote commitments and consumption history, creates `charge_management_settings`, adds quote validity windows, seeds 32 common charge components with default `charge_date_basis` metadata, and seeds the standard business date profiles used for exchange-rate fallback chains. It also creates persistent allocation profiles, repository ID sequences, FX rate sources, and directional FX rates. Business-date assignments persist owner scope, Ocean/Air house shipment scope, and business purpose with a single effective assignment slot across profiles. Charge documents persist shipment scope, and charge lines persist date-basis, allocation, and selected-FX snapshots.

Verify:

```powershell
.\.venv\Scripts\python.exe scripts\check_database.py
```

Expected:

```text
alembic_version=0012_fx_rates_and_sequences
charge_component_count=32
fx_rate_source_count=1
quotation_policy=OPTIONAL
quote_acceptance_mode=CUSTOMER_ACCEPTANCE
provider_cost_layer_enabled=False
```

## 5. Run API

```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/openapi.json
```

## 6. Call API

The default auth adapter requires a bearer token and accepts neutral identity headers. Replace this adapter when integrating with a real identity provider.

```powershell
$headers = @{
  Authorization = "Bearer local-dev-token"
  "X-Subject" = "developer@example.com"
  "X-Roles" = "ADMIN"
}

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/charge-management/initialization-data" `
  -Headers $headers
```

## 7. Generate OpenAPI Artifact

```powershell
.\.venv\Scripts\python.exe scripts\export_openapi.py
```

Output:

```text
app\contracts\charge-management-api.openapi.json
```

## 8. Run Tests

```powershell
.\.venv\Scripts\pytest.exe -q
```

The tests validate the reusable HTTP contract, SQLAlchemy restart persistence, fresh SQLite migrations, FX maintenance and resolution, and the quote-to-export lifecycle.

The reusable API exposes setup values in initialization data. `quotation_policy` defaults to `OPTIONAL`; set it to `REQUIRED` when direct charge documents should be blocked, or `DIRECT_ONLY` when quote requests should be blocked. `quote_acceptance_mode` defaults to `CUSTOMER_ACCEPTANCE`; use `AUTO_ACCEPT` only when the consuming application should award the first rated option automatically. `provider_cost_layer_enabled` defaults to `false`, meaning rating can use customer-pricing contracts without requiring provider-cost contracts.

## 9. Migration Operations

Show current DB version:

```powershell
.\.venv\Scripts\alembic.exe current
```

Show available migrations:

```powershell
.\.venv\Scripts\alembic.exe history
```

Create a future migration:

```powershell
.\.venv\Scripts\alembic.exe revision --autogenerate -m "describe change"
```

Apply latest:

```powershell
.\.venv\Scripts\alembic.exe upgrade head
```

Rollback one migration in local development only:

```powershell
.\.venv\Scripts\alembic.exe downgrade -1
```

## 10. Troubleshooting

If `alembic upgrade head` cannot connect, confirm `DATABASE_URL` is set in the same PowerShell session.

If `scripts\check_database.py` reports `charge_component` missing, migrations were not applied to the database targeted by the current `DATABASE_URL`.

If API calls return `401`, include an `Authorization: Bearer ...` header.

If PostgreSQL rejects the URL, use the SQLAlchemy dialect prefix `postgresql+psycopg://`.
