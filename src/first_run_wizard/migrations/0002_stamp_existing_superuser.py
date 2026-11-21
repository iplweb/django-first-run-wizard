"""Stamp ``admin_created_at`` on installs that already have a superuser.

From 0.3.0 the first-admin step looks at superusers (and this stamp), not at
"any user". Existing installs whose admin was created outside the wizard
get the stamp here, so the step is closed for good before the first request.
"""

from django.conf import settings
from django.db import migrations
from django.utils import timezone


def stamp_existing_superuser(apps, schema_editor):
    State = apps.get_model("first_run_wizard", "FirstRunWizardState")
    User = apps.get_model(settings.AUTH_USER_MODEL)
    if not User._default_manager.filter(is_superuser=True).exists():
        return
    State.objects.get_or_create(pk=1)
    State.objects.filter(pk=1, admin_created_at__isnull=True).update(
        admin_created_at=timezone.now()
    )


class Migration(migrations.Migration):
    dependencies = [
        ("first_run_wizard", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(stamp_existing_superuser, migrations.RunPython.noop),
    ]
