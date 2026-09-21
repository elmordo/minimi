# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-09-21

### Changed

- Renamed project/package from `minimi` to `minimi-para` to resolve a name conflict on PyPI.
- Bumped `sa-values` dependency requirement to `>=0.2.0,<0.3`.

## [0.1.0] - 2026-09-13

### Added

- Initial release of `minimi`, a lightweight database migration tool for SQLAlchemy.
- `Minimi` class supporting forward migration application (`apply()`) and rollback (`rollback()`).
- Migration state tracking using `sa-values` key-value storage on the target database connection.
- Support for defining migrations as raw SQL strings or callable Python functions (`MigrationCallback`).
- Support for multi-step migrations with forward (`up`) and rollback (`down`) operations.
- Automatic rollback of previous steps within a migration module if a subsequent step fails.
- Migration normalization and validation utilities (`normalize_migration_steps`, `get_migration_name`).
- Core exception hierarchy (`MinimiException`, `MigrationFailedError`, `InvalidModuleStructureError`).
