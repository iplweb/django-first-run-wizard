"""django-first-run-wizard — pluggable first-run setup wizard for Django."""

from first_run_wizard.registry import registry
from first_run_wizard.steps import SetupStep

__all__ = ["SetupStep", "registry"]

default_app_config = "first_run_wizard.apps.FirstRunWizardConfig"
