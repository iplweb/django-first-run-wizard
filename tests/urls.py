from django.http import HttpResponse
from django.urls import include, path


def home(request):
    return HttpResponse("home")


urlpatterns = [
    path("", home, name="home"),
    path(
        "setup/",
        include("first_run_wizard.urls", namespace="first_run_wizard"),
    ),
]
