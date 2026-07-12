"""Single-row state table backing the first-run wizard.

There is exactly one row (``pk=1``), created by the initial migration. It
records two moments in an install's life:

* ``admin_created_at`` — set, under a row lock, the instant the first
  superuser is created. It is the transactional guard that makes concurrent
  admin-creation POSTs resolve to a single winner (see
  :func:`first_run_wizard.builtin_steps.admin_user.create_first_admin`).
* ``completed_at`` — set once *every* registered step is satisfied. Its
  presence lets the middleware disable itself (``MiddlewareNotUsed``) so a
  finished install runs no wizard queries per request, and makes the
  ``/setup/`` views return 404.

The flag lives in the database on purpose (not a cache): resetting or
reloading the database — a routine dev operation — must also re-open the
wizard. A cache surviving a DB reset would wrongly report setup as done.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone


class FirstRunWizardState(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    admin_created_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "first-run wizard state"

    def __str__(self) -> str:
        return f"FirstRunWizardState(completed_at={self.completed_at!r})"

    @classmethod
    def load(cls) -> FirstRunWizardState:
        """Return the singleton row, creating it if it is somehow absent.

        The migration ships the row, but a hand-deleted row or a partially
        applied database should not blow up read paths.
        """
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @classmethod
    def is_completed(cls) -> bool:
        """Whether setup has been marked complete (a single cheap PK read)."""
        return cls.objects.filter(pk=1, completed_at__isnull=False).exists()

    @classmethod
    def mark_completed(cls) -> None:
        """Stamp ``completed_at`` once, idempotently.

        ``filter(...).update()`` with the ``isnull`` guard means the first
        writer wins and concurrent callers no-op — no read-modify-write race.
        """
        cls.objects.get_or_create(pk=1)
        cls.objects.filter(pk=1, completed_at__isnull=True).update(
            completed_at=timezone.now()
        )
