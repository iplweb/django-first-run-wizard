"""Built-in steps shipped with django-first-run-wizard.

Importing this module registers them. Override or unregister in your own
AppConfig.ready() if needed.
"""

from first_run_wizard.builtin_steps.admin_user import AdminUserCreationStep
from first_run_wizard.registry import StepAlreadyRegistered, registry

__all__ = ["AdminUserCreationStep"]


def _safe_register(step):
    try:
        registry.register(step)
    except StepAlreadyRegistered:
        pass


_safe_register(AdminUserCreationStep())
