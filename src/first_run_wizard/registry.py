"""Global registry of setup steps."""

from __future__ import annotations

from dataclasses import dataclass

from first_run_wizard.steps import SetupStep


@dataclass(frozen=True)
class WizardInspection:
    """Result of a single pass over all steps.

    ``next_step``: the first incomplete step the *current request* may access
    (None if nothing is both pending and accessible, e.g. an anonymous user
    facing only superuser-only steps, or a request-less inspection).

    ``all_complete``: True only if every registered step reports complete.
    Independent of the request — it drives completion marking.
    """

    next_step: SetupStep | None
    all_complete: bool


class StepAlreadyRegistered(ValueError):
    pass


class StepNotRegistered(KeyError):
    pass


class SetupRegistry:
    def __init__(self):
        self._steps: dict[str, SetupStep] = {}

    def register(self, step: SetupStep) -> None:
        if step.name in self._steps:
            raise StepAlreadyRegistered(
                f"A step with name {step.name!r} is already registered"
            )
        self._steps[step.name] = step

    def unregister(self, name: str) -> None:
        if name not in self._steps:
            raise StepNotRegistered(name)
        del self._steps[name]

    def get(self, name: str) -> SetupStep:
        try:
            return self._steps[name]
        except KeyError as e:
            raise StepNotRegistered(name) from e

    def all_steps(self) -> list[SetupStep]:
        """Return all registered steps, sorted by `order` then `name`."""
        return sorted(self._steps.values(), key=lambda s: (s.order, s.name))

    def inspect(self, request=None) -> WizardInspection:
        """Walk every step once, reporting the next accessible step and
        whether all steps are complete.

        `request` may be None for a request-less inspection (e.g. deciding at
        middleware construction whether setup is finished) — then `next_step`
        is always None, but `all_complete` is still computed.

        If any step's `is_complete()` raises (DB not ready — migrations
        running, etc.) the pass bails out safely: nothing is provably
        complete, so `all_complete=False` and `next_step=None` (don't block).
        """
        next_step = None
        all_complete = True
        for step in self.all_steps():
            try:
                complete = step.is_complete()
            except Exception:
                # DB not ready — treat as not-complete and non-blocking.
                return WizardInspection(next_step=None, all_complete=False)
            if complete:
                continue
            all_complete = False
            if (
                next_step is None
                and request is not None
                and step.is_accessible(request)
            ):
                next_step = step
        return WizardInspection(next_step=next_step, all_complete=all_complete)

    def get_next_incomplete_step(self, request) -> SetupStep | None:
        """First incomplete step the current request may access, or None.

        Thin wrapper over `inspect()` kept for backward compatibility.
        """
        return self.inspect(request).next_step

    def clear(self) -> None:
        """Reset the registry (test-only helper)."""
        self._steps.clear()


registry = SetupRegistry()
