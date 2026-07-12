"""Generic per-step view + status view."""

from __future__ import annotations

from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import FormView

from first_run_wizard.exceptions import SetupAlreadyClaimed
from first_run_wizard.models import FirstRunWizardState
from first_run_wizard.registry import registry


class WizardStepView(FormView):
    """Renders and processes the form for a single named step.

    The URL conf passes the step's `name`; this view looks it up in the
    registry. If the step is already complete, redirects to '/'.
    """

    def get_step(self):
        name = self.kwargs.get("name")
        try:
            return registry.get(name)
        except KeyError as e:
            raise Http404(f"No setup step registered with name {name!r}") from e

    def dispatch(self, request, *args, **kwargs):
        if FirstRunWizardState.is_completed():
            # Setup is closed for good — deleting a user/uczelnia must not
            # reopen the wizard. Re-open only via the management command.
            raise Http404
        step = self.get_step()
        if step.is_complete():
            return redirect("/")
        if not step.is_accessible(request):
            return redirect("/")
        self.step = step
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        return [self.step.template_name]

    def get_form_class(self):
        return self.step.form_class

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(self.step.get_form_kwargs(self.request))
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["step"] = self.step
        ctx["title"] = self.step.verbose_name
        ctx.update(self.step.get_context(self.request))
        return ctx

    def form_valid(self, form):
        try:
            self.step.on_complete(form, self.request)
        except SetupAlreadyClaimed:
            # Lost a race — another request already completed this step.
            # Re-render the form with an error instead of a 500.
            form.add_error(
                None,
                _("This step was just completed by someone else."),
            )
            return self.form_invalid(form)
        return redirect(self.step.get_success_url(self.request))


class StatusView(View):
    """Read-only summary of all steps and their completion status."""

    template_name = "first_run_wizard/status.html"

    def get(self, request):
        if FirstRunWizardState.is_completed():
            raise Http404
        steps_info = []
        for step in registry.all_steps():
            try:
                done = step.is_complete()
            except Exception:
                done = False
            steps_info.append({"step": step, "is_complete": done})

        all_done = (
            all(item["is_complete"] for item in steps_info) if steps_info else True
        )
        return render(
            request,
            self.template_name,
            {"steps": steps_info, "all_done": all_done},
        )
