from django.urls import path

from first_run_wizard.views import StatusView, WizardStepView

app_name = "first_run_wizard"

urlpatterns = [
    path("", StatusView.as_view(), name="status"),
    path("step/<slug:name>/", WizardStepView.as_view(), name="step"),
]
