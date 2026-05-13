"""Middleware that redirects to the next incomplete setup step."""

from __future__ import annotations

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

from first_run_wizard.registry import registry

DEFAULT_SKIP_PREFIXES: tuple[str, ...] = (
    "/static/",
    "/media/",
    "/__debug__/",
)

DEFAULT_SKIP_SUBSTRINGS: tuple[str, ...] = ("migrate",)


class FirstRunWizardMiddleware:
    """Redirect every request to the next incomplete wizard step.

    Skips configurable prefixes/substrings (static files, admin login flow,
    the wizard URLs themselves) so the wizard is reachable.

    Configure in `settings.py`:

        FIRST_RUN_WIZARD_SKIP_PREFIXES = ("/metrics/", "/healthz/")
        FIRST_RUN_WIZARD_SKIP_SUBSTRINGS = ("login", "logout")

    Install *after* `AuthenticationMiddleware` so `request.user` is set
    when steps check `is_accessible()`.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not self._should_skip(request):
            redirect_response = self._maybe_redirect(request)
            if redirect_response is not None:
                return redirect_response
        return self.get_response(request)

    def _should_skip(self, request) -> bool:
        path = request.path

        skip_prefixes = (
            tuple(getattr(settings, "FIRST_RUN_WIZARD_SKIP_PREFIXES", ()))
            + DEFAULT_SKIP_PREFIXES
        )
        if any(path.startswith(p) for p in skip_prefixes):
            return True

        try:
            wizard_prefix = reverse("first_run_wizard:status")
        except Exception:
            wizard_prefix = None
        if wizard_prefix and wizard_prefix != "/" and path.startswith(wizard_prefix):
            return True

        skip_substrings = (
            tuple(getattr(settings, "FIRST_RUN_WIZARD_SKIP_SUBSTRINGS", ()))
            + DEFAULT_SKIP_SUBSTRINGS
        )
        if any(s in path for s in skip_substrings):
            return True

        return False

    def _maybe_redirect(self, request):
        next_step = registry.get_next_incomplete_step(request)
        if next_step is None:
            return None
        target = next_step.get_url()
        if request.path == target:
            return None
        return redirect(target)
