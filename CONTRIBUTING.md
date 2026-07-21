# Contributing

Contributions that keep the module generic, documented, and independently deployable are welcome.

## Development Setup

1. Fork and clone the repository.
2. Create a Python 3.11+ virtual environment.
3. Install `python -m pip install -e ".[dev]"`.
4. Set `DATABASE_URL` to a dedicated PostgreSQL database.
5. Run `alembic upgrade head`.
6. Run `python scripts/run_tests.py`.

See [docs/setup.md](docs/setup.md) for platform-specific commands.

## Change Requirements

- Keep schemas, endpoint names, and behavior adapter-neutral.
- Add an Alembic migration for every schema change.
- Add tests for create, list/search, detail, update, lifecycle, and restart persistence where applicable.
- Regenerate OpenAPI with `python scripts/export_openapi.py` and commit the artifact.
- Update documentation and `CHANGELOG.md` when a public contract changes.
- Do not commit credentials, customer data, database files, or generated test reports.

## Pull Requests

Keep each pull request focused. Explain the behavior change, migration impact, security impact, and verification commands. CI must pass on all supported Python versions before merge.

By contributing, you agree that your contribution is licensed under Apache License 2.0.
