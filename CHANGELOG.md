# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases use
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- PostgreSQL migrations widen Alembic's version column before descriptive revision IDs exceed its default length.

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
