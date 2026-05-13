# django-first-run-wizard

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

## Install

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
| `FIRST_RUN_WIZARD_SKIP_PREFIXES` | `()` | Extra URL prefixes the middleware will not redirect (e.g. `("/metrics/", "/healthz/")`). Defaults `/static/`, `/media/`, `/__debug__/` are always included. |
| `FIRST_RUN_WIZARD_SKIP_SUBSTRINGS` | `()` | Extra substrings (e.g. `("login", "logout")`). Default `migrate` is always included. |

The wizard's own URLs (`first_run_wizard:status` and below) are
auto-skipped to avoid redirect loops.

## Requirements

- Python ≥ 3.10
- Django ≥ 5.2 (5.2 LTS and 6.0 are both in CI)

## Development

```bash
git clone https://github.com/iplweb/django-first-run-wizard
cd django-first-run-wizard
uv sync --all-extras
uv run pytest
```

## License

MIT — see [LICENSE](./LICENSE).
