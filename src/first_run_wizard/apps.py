from django.apps import AppConfig


class FirstRunWizardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "first_run_wizard"
    verbose_name = "First-Run Wizard"

    def ready(self):
        from first_run_wizard import builtin_steps  # noqa: F401
