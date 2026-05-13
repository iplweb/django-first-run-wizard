import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
def test_step_is_complete_when_user_exists():
    from first_run_wizard.builtin_steps import AdminUserCreationStep

    step = AdminUserCreationStep()
    assert step.is_complete() is False
    User.objects.create_user(username="x", password="x")  # noqa: S106
    assert step.is_complete() is True


@pytest.mark.django_db
def test_middleware_redirects_to_admin_step_when_no_users():
    response = Client().get("/")
    assert response.status_code == 302
    assert response.url == reverse(
        "first_run_wizard:step", kwargs={"name": "admin_user"}
    )


@pytest.mark.django_db
def test_admin_step_form_renders():
    url = reverse("first_run_wizard:step", kwargs={"name": "admin_user"})
    response = Client().get(url)
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Create administrator" in body or "Create the administrator" in body


@pytest.mark.django_db
def test_admin_step_creates_superuser_and_logs_in():
    client = Client()
    assert User.objects.count() == 0

    url = reverse("first_run_wizard:step", kwargs={"name": "admin_user"})
    response = client.post(
        url,
        {
            "username": "rootadmin",
            "email": "root@example.com",
            "password1": "VeryStrongPw123!",
            "password2": "VeryStrongPw123!",
        },
    )
    assert response.status_code == 302
    assert response.url == "/"

    assert User.objects.count() == 1
    user = User.objects.get(username="rootadmin")
    assert user.email == "root@example.com"
    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.is_active is True

    # Logged in?
    follow = client.get("/")
    assert follow.status_code == 200
    assert follow.content == b"home"


@pytest.mark.django_db
def test_admin_step_rejects_when_user_already_exists():
    User.objects.create_user(username="existing", password="x")  # noqa: S106
    client = Client()
    url = reverse("first_run_wizard:step", kwargs={"name": "admin_user"})
    response = client.get(url)
    # Step is complete → redirect to '/' rather than render the form.
    assert response.status_code == 302
    assert response.url == "/"


@pytest.mark.django_db
def test_status_view_lists_steps():
    url = reverse("first_run_wizard:status")
    response = Client().get(url)
    # The middleware should let /setup/ through (it's the wizard area).
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "admin" in body.lower()
