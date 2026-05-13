"""Middleware-level tests: redirects, skip rules, custom step ordering."""

import pytest
from django import forms
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from django.urls import reverse

from first_run_wizard.registry import registry
from first_run_wizard.steps import SetupStep

User = get_user_model()


class _NoopForm(forms.Form):
    def save(self):
        pass


class _AlwaysIncompleteSuperuserStep(SetupStep):
    name = "fake_tenant"
    verbose_name = "Fake tenant step"
    order = 50
    form_class = _NoopForm
    template_name = "first_run_wizard/admin_user.html"
    requires_superuser = True

    def is_complete(self):
        return False


@pytest.mark.django_db
def test_middleware_lets_static_through():
    # Static prefix is always skipped.
    response = Client().get("/static/some.css")
    # No redirect; we get a 404 from Django because there's no /static/ URL.
    assert response.status_code in (200, 404)


@pytest.mark.django_db
def test_middleware_lets_wizard_urls_through():
    # /setup/step/admin_user/ — the wizard area itself must not redirect.
    url = reverse("first_run_wizard:step", kwargs={"name": "admin_user"})
    response = Client().get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_middleware_does_not_redirect_anonymous_to_superuser_step():
    """Anonymous user can't access a step requiring superuser → middleware
    must not redirect to it (no users yet, so admin step is the next target).
    """
    registry.register(_AlwaysIncompleteSuperuserStep())
    try:
        response = Client().get("/")
        assert response.status_code == 302
        # Should redirect to admin_user (order=0), NOT fake_tenant (order=50,
        # requires_superuser → inaccessible to anonymous).
        assert response.url == reverse(
            "first_run_wizard:step", kwargs={"name": "admin_user"}
        )
    finally:
        registry.unregister("fake_tenant")


@pytest.mark.django_db
def test_middleware_redirects_logged_in_superuser_to_next_step():
    """After admin_user is satisfied and user is logged in as superuser,
    middleware proceeds to fake_tenant."""
    registry.register(_AlwaysIncompleteSuperuserStep())
    try:
        admin = User.objects.create_superuser(
            username="admin",
            email="a@b.c",
            password="VeryStrong123!",  # noqa: S106
        )
        client = Client()
        client.force_login(admin)

        response = client.get("/")
        assert response.status_code == 302
        assert response.url == reverse(
            "first_run_wizard:step", kwargs={"name": "fake_tenant"}
        )
    finally:
        registry.unregister("fake_tenant")


@pytest.mark.django_db
@override_settings(FIRST_RUN_WIZARD_SKIP_PREFIXES=("/api/",))
def test_custom_skip_prefix_setting_honored():
    response = Client().get("/api/anything/")
    # Should NOT be redirected to the wizard (status 404 from Django routing OK).
    assert response.status_code != 302 or "/setup/" not in response.url


@pytest.mark.django_db
def test_no_redirect_when_all_steps_complete():
    User.objects.create_superuser(
        username="admin",
        email="a@b.c",
        password="VeryStrong123!",  # noqa: S106
    )
    response = Client().get("/")
    assert response.status_code == 200
    assert response.content == b"home"
