from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class NotesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "example_project.notes"
    label = "notes"
    verbose_name = _("Notes")

    def ready(self):
        from first_run_wizard import registry
        from first_run_wizard.registry import StepAlreadyRegistered

        from example_project.notes.steps import CreateFirstNoteStep

        try:
            registry.register(CreateFirstNoteStep())
        except StepAlreadyRegistered:
            pass
