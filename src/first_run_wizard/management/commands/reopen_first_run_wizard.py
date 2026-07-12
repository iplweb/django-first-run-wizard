"""Re-open a wizard that was already marked complete.

Clears ``completed_at`` on the singleton state row. The next worker to start
will see the flag unset and re-activate the middleware and ``/setup/`` views.
Because a running worker has already dropped the middleware
(``MiddlewareNotUsed``), the change takes effect only after a **restart**.

The admin-creation lock (``admin_created_at``) is intentionally left alone:
re-opening lets you redo later, project-specific steps — it does not permit
creating a second superuser (the admin step reports complete while any user
exists). Pass ``--reset-admin-flag`` only if you truly need to clear that
guard too (rare; the admin step still refuses while users exist).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from first_run_wizard.models import FirstRunWizardState


class Command(BaseCommand):
    help = "Re-open the first-run wizard (clears completed_at). Needs a restart."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-admin-flag",
            action="store_true",
            help=(
                "Also clear admin_created_at. The admin step still refuses "
                "while any user exists, so this rarely matters."
            ),
        )

    def handle(self, *args, **options):
        state = FirstRunWizardState.load()
        fields = ["completed_at"]
        state.completed_at = None
        if options["reset_admin_flag"]:
            state.admin_created_at = None
            fields.append("admin_created_at")
        state.save(update_fields=fields)
        self.stdout.write(
            self.style.SUCCESS(
                "First-run wizard re-opened. Restart workers for it to take effect."
            )
        )
