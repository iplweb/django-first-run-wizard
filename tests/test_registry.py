import pytest
from django import forms
from django.test import RequestFactory

from first_run_wizard.registry import (
    SetupRegistry,
    StepAlreadyRegistered,
    StepNotRegistered,
)
from first_run_wizard.steps import SetupStep


class _DummyForm(forms.Form):
    pass


def _make_step(name, order=100, complete=False, accessible=True):
    class S(SetupStep):
        pass

    S.name = name
    S.verbose_name = f"step {name}"
    S.order = order
    S.form_class = _DummyForm
    S.template_name = "first_run_wizard/admin_user.html"
    instance = S()
    instance.is_complete = lambda: complete
    instance.is_accessible = lambda req: accessible
    return instance


def test_step_requires_name():
    class S(SetupStep):
        verbose_name = "x"
        form_class = _DummyForm
        template_name = "x.html"

    with pytest.raises(ValueError, match="name must be set"):
        S()


def test_step_requires_form_class():
    class S(SetupStep):
        name = "x"
        verbose_name = "x"
        template_name = "x.html"

    with pytest.raises(ValueError, match="form_class must be set"):
        S()


def test_register_then_get():
    reg = SetupRegistry()
    s = _make_step("foo")
    reg.register(s)
    assert reg.get("foo") is s


def test_double_register_raises():
    reg = SetupRegistry()
    reg.register(_make_step("foo"))
    with pytest.raises(StepAlreadyRegistered):
        reg.register(_make_step("foo"))


def test_unregister_missing_raises():
    reg = SetupRegistry()
    with pytest.raises(StepNotRegistered):
        reg.unregister("nope")


def test_all_steps_sorted_by_order_then_name():
    reg = SetupRegistry()
    reg.register(_make_step("b", order=10))
    reg.register(_make_step("a", order=100))
    reg.register(_make_step("c", order=10))
    names = [s.name for s in reg.all_steps()]
    assert names == ["b", "c", "a"]  # order=10 first, then alphabetical


def test_get_next_incomplete_step_returns_first_incomplete():
    reg = SetupRegistry()
    reg.register(_make_step("a", order=0, complete=True))
    reg.register(_make_step("b", order=1, complete=False))
    reg.register(_make_step("c", order=2, complete=False))
    rf = RequestFactory()
    next_step = reg.get_next_incomplete_step(rf.get("/"))
    assert next_step.name == "b"


def test_get_next_incomplete_step_skips_inaccessible():
    reg = SetupRegistry()
    reg.register(_make_step("a", order=0, complete=False, accessible=False))
    reg.register(_make_step("b", order=1, complete=False, accessible=True))
    rf = RequestFactory()
    next_step = reg.get_next_incomplete_step(rf.get("/"))
    assert next_step.name == "b"


def test_get_next_incomplete_step_returns_none_when_all_done():
    reg = SetupRegistry()
    reg.register(_make_step("a", complete=True))
    rf = RequestFactory()
    assert reg.get_next_incomplete_step(rf.get("/")) is None


def test_get_next_incomplete_handles_is_complete_exception():
    """If is_complete raises (e.g. DB not yet migrated), return None so the
    request goes through — middleware should not block migrations."""
    reg = SetupRegistry()

    bad = _make_step("a")

    def _boom():
        raise RuntimeError("no table")

    bad.is_complete = _boom
    reg.register(bad)
    rf = RequestFactory()
    assert reg.get_next_incomplete_step(rf.get("/")) is None
