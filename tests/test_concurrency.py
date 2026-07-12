"""Real concurrency test for the admin-creation lock.

This is the regression guard for 0.2.0's headline guarantee: two simultaneous
first-superuser submissions must resolve to exactly one superuser. It runs
only on a backend that supports ``SELECT ... FOR UPDATE`` — on SQLite the
lock silently no-ops (``has_select_for_update = False``) *and* each in-memory
connection is a separate database, so the race cannot be exercised there and
the test skips. CI runs it against PostgreSQL.
"""

import threading

import pytest
from django.contrib.auth import get_user_model
from django.db import connection, connections


@pytest.mark.django_db(transaction=True)
def test_concurrent_admin_creation_yields_exactly_one_superuser():
    if not connection.features.has_select_for_update:
        pytest.skip("backend has no SELECT ... FOR UPDATE (e.g. SQLite)")

    from first_run_wizard.builtin_steps.admin_user import (
        SetupAlreadyClaimed,
        create_first_admin,
    )
    from first_run_wizard.models import FirstRunWizardState

    # Seed the singleton row before the race. transaction=True flushes tables
    # between tests, so the migration's row may be gone; create_first_admin
    # would self-heal it, but pre-seeding keeps the race about the lock alone.
    FirstRunWizardState.load()

    barrier = threading.Barrier(2)
    results: dict[str, str] = {}

    def worker(name: str) -> None:
        barrier.wait()  # release both threads together to contend for the lock
        try:
            create_first_admin(
                username=name,
                email=f"{name}@example.com",
                password="VeryStrongPw123!",
            )
            results[name] = "created"
        except SetupAlreadyClaimed:
            results[name] = "rejected"
        finally:
            connections.close_all()  # close this thread's own connection

    threads = [
        threading.Thread(target=worker, args=(name,)) for name in ("alpha", "beta")
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    User = get_user_model()
    assert User.objects.filter(is_superuser=True).count() == 1
    assert sorted(results.values()) == ["created", "rejected"]
    assert FirstRunWizardState.load().admin_created_at is not None
