from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path


def home(request):
    return HttpResponse(
        "<h1>Welcome</h1><p>The site is live. <a href='/admin/'>Open admin</a>.</p>"
    )


urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path(
        "setup/",
        include("first_run_wizard.urls", namespace="first_run_wizard"),
    ),
]
