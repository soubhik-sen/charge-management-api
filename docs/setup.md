# Setup And Operations

## Prerequisites

- Python 3.11 or newer.
- PostgreSQL 14 or newer for development and deployment.
- Alembic-compatible database credentials with schema migration rights.

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

Swagger UI is at `http://127.0.0.1:8000/docs`. All charge-management operations require a bearer token.

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
