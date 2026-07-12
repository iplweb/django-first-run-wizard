"""Tests for the FirstRunWizardState singleton and the guarantees it backs.

Two problems this model solves:

1. A finished install should pay *zero* per-request DB cost — the middleware
   disables itself (``MiddlewareNotUsed``) once ``completed_at`` is set.
2. Concurrent admin-creation POSTs must produce exactly one superuser — the
   singleton row is a transactional lock (``select_for_update``).
"""

import pytest

pytestmark = pytest.mark.django_db


def test_state_singleton_row_exists_and_loads():
    from first_run_wizard.models import FirstRunWizardState

    state = FirstRunWizardState.load()
    assert state.pk == 1
    assert state.completed_at is None
    assert state.admin_created_at is None
    # load() is idempotent — never a second row.
    FirstRunWizardState.load()
    assert FirstRunWizardState.objects.count() == 1


def test_create_first_admin_stamps_lock_and_creates_superuser():
    from django.contrib.auth import get_user_model

    from first_run_wizard.builtin_steps.admin_user import create_first_admin
    from first_run_wizard.models import FirstRunWizardState

    user = create_first_admin(
        username="admin", email="a@b.c", password="VeryStrong123!"
    )

    assert user.is_superuser
    assert get_user_model().objects.count() == 1
    assert FirstRunWizardState.load().admin_created_at is not None


def test_create_first_admin_rejects_second_winner():
    """The post-lock re-check is the real guard: once an admin exists (or the
    lock is stamped), a second attempt is refused — no second superuser.

    NOTE: this is *sequential* — it validates the re-check branching logic
    only. The actual `select_for_update` lock under genuine concurrency is
    exercised on PostgreSQL by tests/test_concurrency.py (SQLite no-ops the
    lock, so it cannot be tested here)."""
    from django.contrib.auth import get_user_model

    from first_run_wizard.builtin_steps.admin_user import (
        SetupAlreadyClaimed,
        create_first_admin,
    )

    create_first_admin(username="first", email="a@b.c", password="VeryStrong123!")

    with pytest.raises(SetupAlreadyClaimed):
        create_first_admin(username="second", email="d@e.f", password="AnotherStrong9!")

    assert get_user_model().objects.count() == 1
    assert get_user_model().objects.get().username == "first"


def test_step_view_turns_already_claimed_into_form_error():
    """A step that loses the race (on_complete raises SetupAlreadyClaimed)
    must re-render its form with an error — HTTP 200, never a 500."""
    from django import forms
    from django.test import Client
    from django.urls import reverse

    from first_run_wizard.exceptions import SetupAlreadyClaimed
    from first_run_wizard.registry import registry
    from first_run_wizard.steps import SetupStep

    class _Form(forms.Form):
        field = forms.CharField(required=False)

    class _RaceLoserStep(SetupStep):
        name = "raceloser"
        verbose_name = "Race loser"
        order = 0
        form_class = _Form
        template_name = "first_run_wizard/admin_user.html"

        def is_complete(self):
            return False

        def on_complete(self, form, request):
            raise SetupAlreadyClaimed

    registry.clear()  # this becomes the only (next) step; fixture restores after
    registry.register(_RaceLoserStep())

    url = reverse("first_run_wizard:step", kwargs={"name": "raceloser"})
    response = Client().post(url, {"field": "x"})

    assert response.status_code == 200
    assert response.context["form"].non_field_errors()


def test_completed_flag_disables_middleware_redirect():
    """With completed_at set, the middleware must self-disable — even though
    the user table is empty (admin step incomplete) it must NOT redirect.

    Contrast: test_middleware_redirects_to_admin_step_when_no_users proves the
    redirect *does* happen without the flag.
    """
    from django.test import Client
    from django.utils import timezone

    from first_run_wizard.models import FirstRunWizardState

    state = FirstRunWizardState.load()
    state.completed_at = timezone.now()
    state.save()

    response = Client().get("/")
    assert response.status_code == 200
    assert response.content == b"home"


def test_completion_is_stamped_on_first_request_after_last_step():
    """Per-request path: middleware active at construction (no admin yet),
    admin created mid-session, next normal request stamps completed_at."""
    from django.test import Client
    from django.urls import reverse

    from first_run_wizard.models import FirstRunWizardState

    client = Client()
    step_url = reverse("first_run_wizard:step", kwargs={"name": "admin_user"})
    client.post(
        step_url,
        {
            "username": "root",
            "email": "root@example.com",
            "password1": "VeryStrongPw123!",
            "password2": "VeryStrongPw123!",
        },
    )
    assert FirstRunWizardState.load().completed_at is None  # not yet observed

    client.get("/")  # a normal request observes all-complete and stamps it
    assert FirstRunWizardState.load().completed_at is not None


def test_repair_path_backfills_flag_for_legacy_install():
    """Construction repair: an install predating the state row (admin exists,
    completed_at never written) is backfilled and disabled on first request."""
    from django.contrib.auth import get_user_model
    from django.test import Client

    from first_run_wizard.models import FirstRunWizardState

    get_user_model().objects.create_superuser(
        username="admin", email="a@b.c", password="VeryStrong123!"
    )
    assert FirstRunWizardState.load().completed_at is None

    response = Client().get("/")
    assert response.status_code == 200
    assert response.content == b"home"
    assert FirstRunWizardState.load().completed_at is not None


def test_setup_views_404_after_completion():
    """Once completed_at is set, /setup/ is closed for good — deleting the
    admin or the uczelnia must NOT reopen the wizard. (No users here, so the
    step is technically incomplete, yet the view must still 404.)"""
    from django.test import Client
    from django.urls import reverse
    from django.utils import timezone

    from first_run_wizard.models import FirstRunWizardState

    state = FirstRunWizardState.load()
    state.completed_at = timezone.now()
    state.save()

    step_url = reverse("first_run_wizard:step", kwargs={"name": "admin_user"})
    assert Client().get(step_url).status_code == 404

    status_url = reverse("first_run_wizard:status")
    assert Client().get(status_url).status_code == 404


def test_reopen_command_clears_completed_flag():
    """Emergency re-open: the management command clears completed_at so a new
    worker re-activates the wizard (takes effect after a restart)."""
    from django.core.management import call_command
    from django.utils import timezone

    from first_run_wizard.models import FirstRunWizardState

    state = FirstRunWizardState.load()
    state.completed_at = timezone.now()
    state.save()

    call_command("reopen_first_run_wizard")

    assert FirstRunWizardState.load().completed_at is None


def test_middleware_stays_active_when_db_not_ready(monkeypatch):
    """A fresh DB whose table isn't migrated yet must NOT crash worker/
    runserver startup: the construction read degrades to 'wizard active'."""
    from django.db import OperationalError

    from first_run_wizard import middleware as mw

    class _Boom:
        def only(self, *a, **k):
            raise OperationalError("no such table: first_run_wizard_state")

    monkeypatch.setattr(mw.FirstRunWizardState, "objects", _Boom())

    # Must not raise (neither MiddlewareNotUsed nor the DB error).
    instance = mw.FirstRunWizardMiddleware(lambda request: "response")
    assert instance._setup_complete is False


def test_inspect_is_non_blocking_when_a_step_raises():
    """If a step's is_complete() raises (DB not ready), inspect() reports
    nothing complete and no next step — never blocks the request."""
    from django import forms

    from first_run_wizard.registry import registry
    from first_run_wizard.steps import SetupStep

    class _F(forms.Form):
        pass

    class _BoomStep(SetupStep):
        name = "boom"
        verbose_name = "boom"
        order = 0
        form_class = _F
        template_name = "first_run_wizard/admin_user.html"

        def is_complete(self):
            raise RuntimeError("db down")

    registry.clear()  # fixture restores builtins afterwards
    registry.register(_BoomStep())

    result = registry.inspect(request=None)
    assert result.all_complete is False
    assert result.next_step is None
