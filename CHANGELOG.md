# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases use
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Effective-dated rate-book metadata, percentage rates, deterministic rate-entry priority, contract-line context, and quote chargeable weight.
- Explicit charge-line calculation/allocation execution state and migration `0016_align_charge_runtime`.
- Regression tests for overlapping rate rows, percentage-only rates, and repeated invoice components.

### Fixed

- PostgreSQL migrations widen Alembic's version column before descriptive revision IDs exceed its default length.
- Direct runtime and test dependencies are pinned so generated OpenAPI and CI results are reproducible.
- Contract rating now excludes inactive, expired, out-of-scale, and dimension-mismatched rows and never creates zero-line options.
- Invoice matching now aggregates repeated components from posting lines on the correct payer/payee side.

### Documentation

- Added a module-by-module concepts and usage guide covering setup, pricing, allocation, business dates, FX, quotes, charge documents, invoices, and export.

## [0.2.0] - 2026-07-21

### Added

- SQLAlchemy and Alembic persistence for the complete charge domain.
- Maintainable allocation profiles, business-date profiles, assignments, FX sources, and FX rates.
- Directional FX resolution with exact/prior-date and inverse-pair behavior.
- Configurable JWT verification using JWKS or a shared secret.
- PostgreSQL CI, JUnit and coverage reports, Docker quickstart, and public project documentation.

### Changed

- The runtime repository is database-backed; in-memory storage is no longer the runtime persistence model.
- FX resolution defaults deterministically to the `DIRECT` conversion method.

[Unreleased]: https://github.com/soubhik-sen/charge-management-api/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/soubhik-sen/charge-management-api/releases/tag/v0.2.0
