# Quickstart

## Option 1: Docker Compose

```bash
docker compose up --build
```

Wait for the API to start, then call:

```bash
curl -H "Authorization: Bearer local-dev-token" \
  http://localhost:8000/api/v1/charge-management/initialization-data
```

Open `http://localhost:8000/docs` for interactive Swagger documentation. Choose **Authorize** and enter `local-dev-token`.

Stop services with `docker compose down`. Add `--volumes` only when you intentionally want to delete the local PostgreSQL data volume.

The compose file is an evaluation profile and sets `AUTH_MODE=development`. Never expose that profile as a production deployment.

## Option 2: Python And SQLite

This path is convenient for evaluating the API without PostgreSQL.

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
export DATABASE_URL=sqlite:///./charge_management.db
export AUTH_MODE=development
alembic upgrade head
uvicorn app.main:app --reload
```

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
$env:DATABASE_URL = "sqlite:///./charge_management.db"
$env:AUTH_MODE = "development"
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

Use PostgreSQL before evaluating transaction/concurrency behavior or deploying the service.

## First Persistent Objects

Continue with [API examples](api-examples.md) to create and publish an allocation profile, create and assign a business-date profile, maintain an FX rate, and convert an amount.

For real JWT verification, follow [Authentication](authentication.md).
