from django import forms

from example_project.notes.models import Note


class FirstNoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ("title", "body")
