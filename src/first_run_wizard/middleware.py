"""Middleware that redirects to the next incomplete setup step.

A finished install pays nothing: once ``completed_at`` is set the middleware
raises ``MiddlewareNotUsed`` at construction and Django drops it from the
chain for the life of the worker — zero wizard queries per request.

During setup it walks the registry once per request (``registry.inspect``)
to find the next step and to notice the moment the last step is done, at
which point it stamps ``completed_at`` so the *next* worker self-disables.
"""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.shortcuts import redirect
from django.urls import reverse

from first_run_wizard.models import FirstRunWizardState
from first_run_wizard.registry import registry

DEFAULT_SKIP_PREFIXES: tuple[str, ...] = (
    "/static/",
    "/media/",
    "/__debug__/",
    "/admin/",
)

DEFAULT_SKIP_SUBSTRINGS: tuple[str, ...] = ("migrate",)


class FirstRunWizardMiddleware:
    """Redirect every request to the next incomplete wizard step.

    Skips configurable prefixes/substrings (static files, the admin site,
    the wizard URLs themselves) so the wizard is reachable and so the
    superuser can still get into Django admin while project-specific
    steps are pending.

    Configure in `settings.py`:

        FIRST_RUN_WIZARD_SKIP_PREFIXES = ("/metrics/", "/healthz/")
        FIRST_RUN_WIZARD_SKIP_SUBSTRINGS = ("login", "logout")

    These are *additive* — they extend the always-on defaults above
    (`/static/`, `/media/`, `/__debug__/`, `/admin/`). If your project
    mounts admin under a non-default URL, add that prefix here.

    Install *after* `AuthenticationMiddleware` so `request.user` is set
    when steps check `is_accessible()`.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Once a request proves setup is finished, this instance stops
        # touching the registry for the rest of its life.
        self._setup_complete = False
        if self._install_is_finished():
            # Finished install → don't run at all. Django removes us from
            # the middleware chain; per-request cost drops to zero.
            raise MiddlewareNotUsed

    def _install_is_finished(self) -> bool:
        """True only if setup is provably complete; False on any doubt.

        Reads the ``completed_at`` flag. If it is unset but every step is
        already satisfied (an install upgraded from a pre-state package
        version), backfill the flag and report finished. Any DB-not-ready
        condition — missing table before migrations, connection down —
        returns False so the wizard stays active rather than crashing
        worker/`runserver` startup.
        """
        try:
            state = (
                FirstRunWizardState.objects.only("completed_at").filter(pk=1).first()
            )
        except Exception:
            # Table missing (migrations not applied) or DB down → not
            # finished; keep the wizard active. Safe default.
            return False

        if state is None:
            # Singleton row absent (pre-migration / hand-deleted) — can't
            # fast-path; let the per-request logic run (it self-heals).
            return False

        if state.completed_at:
            return True

        # Repair path: flag unset but maybe every step is already done.
        if registry.inspect().all_complete:
            FirstRunWizardState.mark_completed()
            return True
        return False

    def __call__(self, request):
        if self._setup_complete:
            return self.get_response(request)

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
        inspection = registry.inspect(request)
        if inspection.all_complete:
            # Last step just finished. Record it so the next worker
            # self-disables, and short-circuit this instance from now on.
            FirstRunWizardState.mark_completed()
            self._setup_complete = True
            return None
        next_step = inspection.next_step
        if next_step is None:
            return None
        target = next_step.get_url()
        if request.path == target:
            return None
        return redirect(target)
