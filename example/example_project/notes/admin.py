from django.contrib import admin

from example_project.notes.models import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("id", "title")
    search_fields = ("title", "body")
    ordering = ("-id",)
