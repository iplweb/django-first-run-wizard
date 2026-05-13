from django.contrib import admin
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.urls import include, path

from example_project.notes.models import Note


def home(request):
    note_exists = Note.objects.exists()
    user_exists = get_user_model().objects.exists()
    user = request.user

    if note_exists and user.is_authenticated:
        body = (
            "<p>The Note was created in the site-specific "
            "<code>first_note</code> wizard step — that's why you can see "
            "this page.</p>"
            f"<p>You are logged in as <strong>{user.get_username()}</strong>, "
            "the admin user created by the built-in <code>admin_user</code> "
            "step. The wizard signs you in automatically on form submit.</p>"
        )
    elif note_exists:
        body = (
            "<p>The admin user and the first Note have been created, "
            "but you are not currently logged in.</p>"
            "<p>Open <a href='/admin/'>/admin/</a> and sign in to manage the "
            "site.</p>"
        )
    elif user_exists:
        body = (
            "<p>The admin user has been created, but the first Note has "
            "<strong>not</strong> been created yet — log in as the admin "
            "user via <a href='/admin/'>/admin/</a>; on the next request "
            "the wizard will redirect you to the <code>first_note</code> "
            "step.</p>"
        )
    else:
        body = (
            "<p>Setup is not complete. Visit <a href='/setup/'>/setup/</a> "
            "to start the wizard.</p>"
        )

    return HttpResponse(
        "<h1>Welcome</h1>"
        f"{body}"
        "<hr>"
        "<p><a href='/admin/'>Open admin</a> &middot; "
        "<a href='/setup/'>Wizard status</a></p>"
    )


urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path(
        "setup/",
        include("first_run_wizard.urls", namespace="first_run_wizard"),
    ),
]
