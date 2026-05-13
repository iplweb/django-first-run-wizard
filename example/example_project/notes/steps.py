from first_run_wizard import SetupStep

from example_project.notes.forms import FirstNoteForm
from example_project.notes.models import Note


class CreateFirstNoteStep(SetupStep):
    name = "first_note"
    verbose_name = "Create your first note"
    order = 100
    form_class = FirstNoteForm
    template_name = "notes/first_note.html"
    requires_superuser = True

    def is_complete(self):
        return Note.objects.exists()
