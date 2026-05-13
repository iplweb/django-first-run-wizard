# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial extraction from `bpp/src/bpp_setup_wizard/` (commit `a1e114c97`).
- Plugin registry: `SetupStep` base class + `registry.register()` API.
- Generic middleware `FirstRunWizardMiddleware` redirecting to the next
  incomplete step; configurable skip prefixes/substrings via
  `FIRST_RUN_WIZARD_SKIP_PREFIXES` / `FIRST_RUN_WIZARD_SKIP_SUBSTRINGS`.
- Generic `WizardStepView` (one URL per step, looked up by name) and
  `StatusView` overview.
- Built-in step `AdminUserCreationStep` — creates first superuser based on
  `settings.AUTH_USER_MODEL`, auto-logs them in.
- Default templates (vendor-neutral inline CSS) that consumers can override
  per `first_run_wizard/<template>.html`.
