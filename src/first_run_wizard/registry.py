"""Global registry of setup steps."""

from __future__ import annotations

from first_run_wizard.steps import SetupStep


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

    def get_next_incomplete_step(self, request) -> SetupStep | None:
        """First step that:

        - is not yet complete, AND
        - the current request is allowed to access (per `is_accessible()`).

        Returns None if everything is done OR the current user can't access
        any pending step (e.g. anonymous user on a superuser-only step —
        middleware should let the request through in that case).
        """
        for step in self.all_steps():
            try:
                complete = step.is_complete()
            except Exception:
                # DB not ready (migrations running, etc.) — treat as not
                # blocking; re-raised as None gives the request a chance.
                return None
            if complete:
                continue
            if not step.is_accessible(request):
                continue
            return step
        return None

    def clear(self) -> None:
        """Reset the registry (test-only helper)."""
        self._steps.clear()


registry = SetupRegistry()
