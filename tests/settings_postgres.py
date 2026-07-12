"""PostgreSQL test settings — used by the concurrency CI leg.

Identical to ``tests.settings`` except ``DATABASES`` points at a real
PostgreSQL so ``select_for_update()`` actually locks rows. SQLite reports
``has_select_for_update = False`` and silently drops the clause, so the
admin-creation race can only be exercised for real here.

Connection parameters come from the environment (the CI ``postgres`` service).
"""

import os

from tests.settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "first_run_wizard"),
        "USER": os.environ.get("POSTGRES_USER", "postgres"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "postgres"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}
