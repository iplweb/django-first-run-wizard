# django-first-run-wizard

[![Tests](https://github.com/iplweb/django-first-run-wizard/actions/workflows/tests.yml/badge.svg)](https://github.com/iplweb/django-first-run-wizard/actions/workflows/tests.yml)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://github.com/iplweb/django-first-run-wizard)
[![Django Version](https://img.shields.io/badge/django-5.2%20LTS%20%7C%206.0-0C4B33)](https://github.com/iplweb/django-first-run-wizard)
[![License: MIT](https://img.shields.io/github/license/iplweb/django-first-run-wizard)](LICENSE)

Pluggable first-run setup wizard for Django. On a fresh install, redirects
every request to a configurable sequence of setup steps. Ships with one
built-in step (create the first superuser); your project plugs in whatever
extras it needs (database seed, tenant config, integration tokens, …).

## Why

Most Django projects need a first-run experience: someone has to create the
first admin user and configure a handful of project-specific settings. The
existing ecosystem covers half of this:

- [`django-formtools`](https://django-formtools.readthedocs.io/) — multi-step
  forms, but no "fresh install" detection or middleware redirect.
- [`django-setup-configuration`](https://pypi.org/project/django-setup-configuration/) —
  Maykin Media's YAML-driven config, no UI.
- `django-initial-setup` — abandoned since 2020, Django 3.1.

This package is the missing piece: **a plugin-based registry of setup
steps with middleware that redirects to the next incomplete one**, so a
fresh install walks an admin through configuration in the browser.

## Features

- **Fresh-install detection** — middleware redirects every request to the next incomplete setup step until the wizard finishes.
- **Plugin registry** — each step is a `SetupStep` subclass registered in `AppConfig.ready()`; ordered by an `order` integer.
- **Built-in admin user step** — creates the first superuser via a `UserCreationForm` adapted to your `AUTH_USER_MODEL`, then logs them in.
- **Replaceable steps** — `registry.unregister("admin_user")` then register your own form/template if the built-in doesn't fit.
- **Access control** — `requires_authentication` / `requires_superuser` flags per step; custom logic via `is_accessible(request)`.
- **Configurable skip rules** — `FIRST_RUN_WIZARD_SKIP_PREFIXES` / `FIRST_RUN_WIZARD_SKIP_SUBSTRINGS` to keep `/metrics/`, `/healthz/`, etc. out of the redirect loop.

## Install

### Using uv (recommended)

```bash
uv add django-first-run-wizard
```

### Using pip

```bash
pip install django-first-run-wizard
```

`settings.py`:

```python
INSTALLED_APPS = [
    # ...
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "first_run_wizard",
]

MIDDLEWARE = [
    # ...
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "first_run_wizard.middleware.FirstRunWizardMiddleware",  # AFTER auth
    "django.contrib.messages.middleware.MessageMiddleware",
]
```

`urls.py`:

```python
from django.urls import include, path

urlpatterns = [
    path("setup/", include("first_run_wizard.urls", namespace="first_run_wizard")),
    # ...
]
```

That's enough to get the **built-in admin step** working: visit any URL on
a fresh install → redirected to `/setup/step/admin_user/` → fill in the
form → user is created, logged in, redirected to `/`.

## Adding your own steps

Subclass `SetupStep`. Register it from an `AppConfig.ready()` hook.

```python
# myproject/onboarding/steps.py
from first_run_wizard import SetupStep
from myproject.tenants.forms import TenantSetupForm
from myproject.tenants.models import Tenant


class CreateTenantStep(SetupStep):
    name = "create_tenant"           # unique slug; URL = /setup/step/create_tenant/
    verbose_name = "Configure your organization"
    order = 100                       # runs after admin_user (order=0)
    form_class = TenantSetupForm
    template_name = "onboarding/create_tenant.html"
    requires_superuser = True         # only the just-created admin can run it

    def is_complete(self):
        return Tenant.objects.exists()
```

```python
# myproject/onboarding/apps.py
from django.apps import AppConfig


class OnboardingConfig(AppConfig):
    name = "myproject.onboarding"

    def ready(self):
        from first_run_wizard import registry
        from myproject.onboarding.steps import CreateTenantStep
        registry.register(CreateTenantStep())
```

The middleware now redirects in this order:

1. Anonymous request, no users → `/setup/step/admin_user/` (built-in).
2. After admin is created and logged in → `/setup/step/create_tenant/`
   (your step, because `requires_superuser=True` and order=100).
3. When `Tenant.objects.exists()` → no more redirects; the site is live.

## Built-in steps

### `AdminUserCreationStep`

- `name = "admin_user"`, `order = 0`
- `is_complete()` checks `get_user_model().objects.exists()`
- Form: `AdminUserCreationForm` (subclass of `UserCreationForm` adapted to
  `settings.AUTH_USER_MODEL`)
- On success: sets `is_staff=True, is_superuser=True, is_active=True`,
  logs the user in via `ModelBackend`

To replace it (e.g. you want a different form / different model fields),
unregister and register your own in `AppConfig.ready()`:

```python
from first_run_wizard import registry

registry.unregister("admin_user")
registry.register(MyCustomAdminStep())
```

## SetupStep API

| Attribute / method | Purpose |
|---|---|
| `name: str` | Unique slug. Used in URLs and registry lookup. |
| `verbose_name: str` | Human-readable label. |
| `order: int` | Lower = runs earlier. Default 100. |
| `form_class` | Django form / ModelForm class. |
| `template_name: str` | Template path. Should `{% extends "first_run_wizard/base.html" %}` (or your own base). |
| `requires_authentication: bool` | If True, anonymous users skip this step. |
| `requires_superuser: bool` | If True, only authenticated superusers see it. |
| `is_complete()` | Return True when the step is satisfied. Called on every request — keep it cheap. |
| `is_accessible(request)` | Override for custom access logic. Default: enforce `requires_*`. |
| `get_form_kwargs(request)` | Extra kwargs for `form_class(**kwargs)`. |
| `get_context(request)` | Extra template context. |
| `on_complete(form, request)` | Hook after `form.is_valid()`. Default: `form.save()`. |
| `get_success_url(request)` | Redirect target after success. Default `/`. |

## Settings

| Setting | Default | Purpose |
|---|---|---|
| `FIRST_RUN_WIZARD_SKIP_PREFIXES` | `()` | Extra URL prefixes the middleware will not redirect (e.g. `("/metrics/", "/healthz/")`). Always-on built-in defaults: `/static/`, `/media/`, `/__debug__/`, `/admin/`. |
| `FIRST_RUN_WIZARD_SKIP_SUBSTRINGS` | `()` | Extra substrings (e.g. `("login", "logout")`). Default `migrate` is always included. |

The wizard's own URLs (`first_run_wizard:status` and below) are
auto-skipped to avoid redirect loops.

### Whitelist of always-accessible URLs

The middleware's defaults are deliberately permissive: `/static/`,
`/media/`, `/__debug__/`, and **`/admin/`** are skipped unconditionally,
which means a logged-in superuser can always reach Django admin — even
while project-specific wizard steps are still pending. Without this,
once `admin_user` was done but, say, `create_tenant` was not, the
superuser would be bounced back to the wizard on every `/admin/*` hit,
making admin effectively unreachable mid-setup.

`FIRST_RUN_WIZARD_SKIP_PREFIXES` extends (not replaces) the built-in
defaults. If your project mounts admin under a non-default URL, add
that prefix:

```python
# settings.py
FIRST_RUN_WIZARD_SKIP_PREFIXES = ("/management/",)  # custom admin path
```

Matching is `path.startswith(prefix)`, so the prefix should include
trailing `/`. Anonymous visitors hitting `/admin/login/` on a fresh
install with no users yet land on Django's default login screen — which
won't accept any credentials, since there are no users — so they
typically discover the wizard via the redirect from `/` instead.

## Supported versions

### Django × Python

| Django  | 3.10 | 3.11 | 3.12 | 3.13 | 3.14 | Status                                 |
|---------|------|------|------|------|------|----------------------------------------|
| 5.2 LTS | ✓    | ✓    | ✓    | ✓    | ✓    | Active LTS (extended support Apr 2028) |
| 6.0     | —    | —    | ✓    | ✓    | ✓    | Mainstream Aug 2026, extended Apr 2027 |

Every ✓ above is covered by the CI matrix in `.github/workflows/tests.yml`.

## Translations

The package ships with English source strings and a Polish translation
(`pl`). All user-facing strings — form labels, validation errors, step
`verbose_name`s, and template content — go through Django's i18n
machinery (`gettext_lazy` / `{% trans %}` / `{% blocktrans %}`).

To activate translations in your project, make sure `LocaleMiddleware`
is in your `MIDDLEWARE` (between `SessionMiddleware` and
`CommonMiddleware`), `USE_I18N = True`, and your `LANGUAGES` list
includes `pl`:

```python
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",  # ← add this
    "django.middleware.common.CommonMiddleware",
    # ...
]

LANGUAGES = [("en", "English"), ("pl", "Polski")]
USE_I18N = True
```

The browser's `Accept-Language` header then selects the active
translation. The bundled `example/` project is wired this way.

### Adding a new language

The library and the bundled `example/` project keep **separate** message
catalogs. `makemessages` scans the filesystem from your current
directory, so each catalog is extracted from its own subtree:

```bash
# Library strings — run from inside the package:
cd src/first_run_wizard
django-admin makemessages -l <lang>      # e.g. de, fr, es, cs
# edit locale/<lang>/LC_MESSAGES/django.po
django-admin compilemessages
```

```bash
# Example-project strings — run from inside example/:
cd example
python manage.py makemessages -l <lang>
# edit locale/<lang>/LC_MESSAGES/django.po
python manage.py compilemessages
```

Do **not** run `makemessages` from the repository root — it would
walk the entire tree, mix library and example strings into whichever
`locale/` it writes to, and silently break the separation. CI has a
`translations` job that re-extracts both catalogs from sources and
fails the build if they drifted, so contamination is caught before
merge.

Requires the `gettext` toolchain (`brew install gettext` on macOS,
`apt install gettext` on Debian/Ubuntu). PRs adding more translations
are welcome.

## Development

```bash
git clone https://github.com/iplweb/django-first-run-wizard
cd django-first-run-wizard
uv sync --all-extras
uv run pytest
```

## License

MIT — see [LICENSE](./LICENSE).
