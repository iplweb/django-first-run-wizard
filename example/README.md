# Example project

Minimal Django project demonstrating `django-first-run-wizard`. Shows:

1. The built-in `admin_user` step (provided by the package).
2. A custom step `first_note` (registered by the `notes` app in
   `example_project/notes/apps.py`).

## Run

From the package root:

```bash
uv sync --all-extras
cd example
uv run python manage.py migrate
uv run python manage.py runserver
```

Visit http://127.0.0.1:8000/ — you'll be redirected through:

1. `/setup/step/admin_user/` — create the superuser
2. `/setup/step/first_note/` — create the first Note (because the
   `CreateFirstNoteStep` declares `requires_superuser=True`)
3. `/` — the home page, once both steps are complete.

`/setup/` shows the overall status page.
