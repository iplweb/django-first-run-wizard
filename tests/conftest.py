import os

import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")


@pytest.fixture(autouse=True)
def _reset_registry_to_builtins():
    """After every test, restore the registry to exactly the built-in steps.

    Tests that add custom steps can rely on a clean slate next time.
    """
    from first_run_wizard.registry import registry

    yield

    registry.clear()
    from first_run_wizard import builtin_steps  # noqa: F401
    from first_run_wizard.builtin_steps import AdminUserCreationStep

    try:
        registry.register(AdminUserCreationStep())
    except Exception:
        pass
