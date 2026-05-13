# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-05-13

### Fixed
- `AdminUserCreationForm` now passes an unsaved `User(username=…, email=…)`
  instance to `password_validation.validate_password()` so
  `UserAttributeSimilarityValidator` actually fires — previously a password
  identical to the username silently passed. This matches the contract used
  by `django.contrib.auth.forms.UserCreationForm`, the Django admin, and the
  `createsuperuser` management command.

### Changed
- Example project (`example/example_project/settings.py`) now ships the
  Django default `AUTH_PASSWORD_VALIDATORS` (UserAttributeSimilarity,
  MinimumLength, CommonPassword, NumericPassword) so the wizard's first-
  superuser step enforces the same rules out of the box.

### Infrastructure
- Test settings (`tests/settings.py`) gained the same default
  `AUTH_PASSWORD_VALIDATORS` block, and the suite now exercises
  too-short-password and password-equals-username rejection paths.

## [0.1.0] - 2026-05-13

### Added
- Initial extraction from `bpp/src/bpp_setup_wizard/` (commit `a1e114c97`).
- Plugin registry: `SetupStep` base class + `registry.register()` API.
- Generic middleware `FirstRunWizardMiddleware` redirecting to the next
  incomplete step; configurable skip prefixes/substrings via
  `FIRST_RUN_WIZARD_SKIP_PREFIXES` / `FIRST_RUN_WIZARD_SKIP_SUBSTRINGS`.
- Generic `WizardStepView` (one URL per step, looked up by name) and
  `StatusView` overview.
- Built-in step `AdminUserCreationStep` — creates first superuser based on
  `settings.AUTH_USER_MODEL`, auto-logs them in via `login()` in
  `on_complete`.
- Default templates (vendor-neutral inline CSS) that consumers can override
  per `first_run_wizard/<template>.html`.
- Polish translation for the library (18 messages) shipped as
  `pl/LC_MESSAGES/django.{po,mo}` in the wheel.
- Example project under `example/` demonstrating a custom step
  (`CreateFirstNoteStep`, `requires_superuser=True`), admin registration
  for the demo `Note` model, and a state-aware home view that explains
  the current wizard state in four branches.
- Polish translation for the example project (17 messages) covering the
  notes model field labels, the step's `verbose_name`, the form template,
  and every branch of the home view.
- Tests for Polish translation activation covering form labels, step
  `verbose_name`, template strings, and the English-default fallback.
- Regression test for the `/admin/` skip prefix.
- README sections: CI/Python/Django/License badges, Features bullet list,
  Django × Python support matrix, `uv add` install, Translations workflow
  documented per locale tree (library vs example), Whitelist of
  always-accessible URLs.

### Changed
- `DEFAULT_SKIP_PREFIXES` now includes `/admin/` — the wizard middleware
  no longer redirects logged-in superusers away from Django admin while
  project-specific steps remain incomplete. `FIRST_RUN_WIZARD_SKIP_PREFIXES`
  remains additive.

### Removed
- Legacy `default_app_config` from `first_run_wizard/__init__.py`
  (deprecated in Django 3.2, removed in 5.1) — handled by `django-upgrade`.

### Fixed
- `pre-commit` `django-upgrade` hook was crashing on `--target-version 5.2`
  (bumped `1.22.2` → `1.30.0`; 5.2 support landed in `1.25.0`).
- CI ruff lint/format jobs were silently passing on failures
  (`|| true` removed).

### Infrastructure
- CI compiles translations before running tests (matrix job) and before
  the example check.
- CI re-extracts both `.po` catalogs and fails on drift — catches strings
  missing from the catalog, lingering removed strings, and cross-tree
  contamination between library and example.
- Third-party GitHub Action `astral-sh/setup-uv` pinned to commit SHA.

[Unreleased]: https://github.com/iplweb/django-first-run-wizard/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/iplweb/django-first-run-wizard/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/iplweb/django-first-run-wizard/releases/tag/v0.1.0
