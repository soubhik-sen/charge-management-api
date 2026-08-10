# Setup And Operations

## Prerequisites

- Python 3.11 or newer.
- PostgreSQL 14 or newer for development and deployment.
- Alembic-compatible database credentials with schema migration rights.
- Flutter stable when running or building the optional web application.

SQLite is supported for a local smoke test, not as the production database.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

On Windows PowerShell, use:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

If activation is restricted, run commands explicitly through `.venv\Scripts\python.exe` and executables under `.venv\Scripts`.

## Configure

Configuration is read from process environment variables. `.env.example` is a reference; the application does not automatically load `.env` files.

PostgreSQL:

```text
DATABASE_URL=postgresql+psycopg://charge_user:charge_password@localhost:5432/charge_management
```

Local SQLite smoke test:

```text
DATABASE_URL=sqlite:///./charge_management.db
```

For a local-only session, set `AUTH_MODE=development`. For every shared or production environment, keep the default `AUTH_MODE=jwt` and configure the variables in [authentication.md](authentication.md).

## Migrate And Verify

```bash
alembic upgrade head
python scripts/check_database.py
```

The database check reports the migration version, seed counts, and charge-management settings without printing database passwords.

Useful migration commands:

```bash
alembic current
alembic history
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Use `alembic downgrade -1` only against a disposable development database after checking whether the migration is safely reversible.

## Run

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Swagger UI is at `http://127.0.0.1:8000/docs`. `/health` is a liveness probe that does not touch the database. `/ready` verifies runtime database connectivity and returns `503 Service Unavailable` if the check fails. All charge-management operations require a bearer token.

## Run The Web Application

```bash
cd apps/ledgerflow_web
flutter pub get
flutter run -d chrome --dart-define=LEDGERFLOW_API_URL=http://127.0.0.1:8000
```

The application starts in demo mode. Connect it to the local API with `local-dev-token` when Docker Compose or `AUTH_MODE=development` is in use. For JWT mode, supply a token issued for the configured issuer and audience. Configure `CORS_ALLOWED_ORIGINS` on the API with the exact web origin, for example `http://localhost:8080`.

For a single-origin local build, compile the UI with the API URL set to the same address, then let FastAPI serve the compiled assets after its API routes:

```bash
cd apps/ledgerflow_web
flutter build web --release \
  --dart-define=LEDGERFLOW_API_URL=http://127.0.0.1:8080 \
  --dart-define=LEDGERFLOW_API_TOKEN=local-dev-token
cd ../..
AUTH_MODE=development \
LEDGERFLOW_WEB_DIRECTORY=apps/ledgerflow_web/build/web \
uvicorn app.main:app --host 127.0.0.1 --port 8080
```

`LEDGERFLOW_WEB_DIRECTORY` is opt-in. When it is unset, the API serves no web assets and Render's separate static-site deployment is unchanged.

## Render

`render.yaml` defines the API, static Flutter UI, and PostgreSQL resources inside the `LEDGERFLOW` project and `Dev & QA` environment. Render's native database URL is normalized to SQLAlchemy's `postgresql+psycopg://` form at startup so the bundled psycopg 3 driver is used. The API runs `alembic upgrade head` before starting Uvicorn and exposes unauthenticated `/health` and `/ready` operational endpoints for liveness and database-backed readiness. The static-site build script installs a cached stable Flutter SDK and compiles `apps/ledgerflow_web` with the Dev & QA API URL.

The Dev & QA Blueprint uses JWT mode with a platform-generated HS256 secret. Use the configured issuer `https://ledgerflow.dev-qa/` and audience `charge-management-api` when minting test tokens. Replace this with your production issuer and JWKS configuration before creating a production environment.

## Generate The Contract

```bash
python scripts/export_openapi.py
```

Commit changes to `app/contracts/charge-management-api.openapi.json` whenever endpoint or DTO behavior changes.

## Validate

```bash
python scripts/run_tests.py
python -m build
```

See [testing.md](testing.md) for report locations and CI behavior.

## Production Checklist

- Run PostgreSQL with backups, encryption, monitoring, and restricted credentials.
- Run `alembic upgrade head` as a controlled deployment step.
- Configure JWT issuer, audience, algorithms, and JWKS over TLS.
- Replace or configure `PolicyAdapter` for action, tenant, and row-scope authorization.
- Terminate TLS at a trusted proxy or service mesh and restrict direct service access.
- Keep `AUTH_MODE=development` out of shared environments.
- Pin and scan the deployed image and dependencies according to your organization policy.
