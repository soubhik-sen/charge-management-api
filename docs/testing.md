# Testing And Reports

## Local Test Suite

```bash
python scripts/run_tests.py
```

This runs the FastAPI request suite, domain lifecycle tests, SQLAlchemy restart-persistence tests, and Alembic migration tests. Requests execute through `TestClient`, so authentication, validation, routing, transaction, response serialization, and persistence behavior are exercised together.

Reports are written to:

- `test-results/summary.md`: human-readable status and counts.
- `test-results/junit.xml`: per-test machine-readable results.
- `test-results/coverage.xml`: machine-readable application coverage.

The directory is ignored by Git because results belong to a particular execution, not the source tree.

## Database Selection

If `DATABASE_URL` is absent, tests create an isolated temporary SQLite database. To validate the actual runtime database, point the suite at a dedicated PostgreSQL database:

```bash
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/charge_management_test
python scripts/run_tests.py
```

The suite resets data and runs migrations. Never point it at a development, staging, or production database containing data you need.

## GitHub Actions

`.github/workflows/ci.yml` runs against PostgreSQL 16 on Python 3.11, 3.12, and 3.13. Every matrix job:

1. Applies all Alembic migrations to a fresh database.
2. Runs the API tests and coverage report.
3. Regenerates OpenAPI and fails on uncommitted contract drift.
4. Builds wheel and source distributions.
5. Uploads `test-results/` as a workflow artifact, even when tests fail.

Open a workflow run in GitHub and download `test-results-python-<version>` from its **Artifacts** section. JUnit-aware CI tools can ingest `junit.xml` directly.

## Contract Verification

Whenever a route or DTO changes:

```bash
python scripts/export_openapi.py
git diff -- app/contracts/charge-management-api.openapi.json
```

Review and commit intentional contract changes. CI rejects stale generated OpenAPI.
