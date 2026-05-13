"""SetupStep base class — subclass to add a step to the wizard."""

from __future__ import annotations

from django.urls import reverse


class SetupStep:
    """One step in the first-run wizard.

    Subclass and override `is_complete()` and `on_complete()`. Register the
    instance with `first_run_wizard.registry.register(MyStep())` — usually
    from `AppConfig.ready()`.
    """

    name: str = ""
    verbose_name: str = ""
    order: int = 100
    form_class = None
    template_name: str = ""
    requires_authentication: bool = False
    requires_superuser: bool = False

    def __init__(self):
        if not self.name:
            raise ValueError(f"{type(self).__name__}.name must be set (unique slug)")
        if not self.form_class:
            raise ValueError(f"{type(self).__name__}.form_class must be set")
        if not self.template_name:
            raise ValueError(f"{type(self).__name__}.template_name must be set")

    def is_complete(self) -> bool:
        """Return True when this step has been satisfied.

        Called by middleware on every request. Keep it cheap — a single
        `.exists()` query is the usual shape.
        """
        raise NotImplementedError

    def get_url(self) -> str:
        """URL of the per-step view."""
        return reverse("first_run_wizard:step", kwargs={"name": self.name})

    def get_form_kwargs(self, request) -> dict:
        """Extra kwargs passed to form_class.__init__()."""
        return {}

    def get_context(self, request) -> dict:
        """Extra context for the step's template."""
        return {}

    def on_complete(self, form, request):
        """Run after `form.is_valid()` passed. Default: `form.save()`."""
        return form.save()

    def get_success_url(self, request) -> str:
        """Where to redirect after this step completes.

        Default: project root. Middleware will then either redirect to the
        next incomplete step or let the response through.
        """
        return "/"

    def is_accessible(self, request) -> bool:
        """May the current request access this step?

        Default rule:
        - public step (no auth flags): always
        - requires_authentication: user must be authenticated
        - requires_superuser: user must be authenticated AND is_superuser
        """
        user = getattr(request, "user", None)
        if self.requires_superuser:
            return bool(
                user and user.is_authenticated and getattr(user, "is_superuser", False)
            )
        if self.requires_authentication:
            return bool(user and user.is_authenticated)
        return True

    def __repr__(self):
        return f"<{type(self).__name__} name={self.name!r} order={self.order}>"
