from django.contrib import admin
from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.urls import include, path

from example_project.notes.models import Note


def home(request):
    return render(
        request,
        "home.html",
        {
            "note_exists": Note.objects.exists(),
            "user_exists": get_user_model().objects.exists(),
        },
    )


urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path(
        "setup/",
        include("first_run_wizard.urls", namespace="first_run_wizard"),
    ),
]
