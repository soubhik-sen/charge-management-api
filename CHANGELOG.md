# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases use
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Separate payment-baseline Business Date Profile purpose, invoice-date event, persisted purpose and FX assignment safeguards (migration `0035_payment_baseline_profile_purpose`).

- Effective-dated rate-book metadata, percentage rates, deterministic rate-entry priority, contract-line context, and quote chargeable weight.
- Explicit charge-line calculation/allocation execution state and migration `0016_align_charge_runtime`.
- Regression tests for overlapping rate rows, percentage-only rates, and repeated invoice components.
- Side-effect-free calculation preview for direct, profile, percentage, FX, and target allocation scenarios.
- Effective-dated allocation and business-date versions with optimistic concurrency controls.
- Draft/publish/retire rate-book version lifecycle with exact rate-entry provenance.
- Database-backed readiness endpoint at `/ready` and complete Flutter list pagination.

### Fixed

- Invoice capture and matching now respect approved/exported/reversed document finality; export retries preserve the existing snapshot without rewriting line states.

- Financial export payloads include only posting lines, preserving calculation lineage in the document workspace without posting it twice.
- PostgreSQL migrations widen Alembic's version column before descriptive revision IDs exceed its default length.
- Direct runtime and test dependencies are pinned so generated OpenAPI and CI results are reproducible.
- Contract rating now excludes inactive, expired, out-of-scale, and dimension-mismatched rows and never creates zero-line options.
- Invoice matching now aggregates repeated components from posting lines on the correct payer/payee side.
- Percentage rates now require and use an explicit monetary base instead of treating the percentage as an amount.
- Quote, offer, document, and invoice totals now enforce a single currency and retain FX conversion provenance.
- Calculation-template steps, named subtotals, preconditions, relationship roles, and statistical rows now execute during contract rating.

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
