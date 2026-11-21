import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
def test_step_is_complete_only_once_a_superuser_exists():
    from first_run_wizard.builtin_steps import AdminUserCreationStep

    step = AdminUserCreationStep()
    assert step.is_complete() is False
    # An ordinary account (e.g. a technical/service account or a demo user
    # created by a data seeder) must not close the step:
    User.objects.create_user(username="x", password="x")  # noqa: S106
    assert step.is_complete() is False
    User.objects.create_superuser(username="root", email="r@example.com", password="r")  # noqa: S106
    assert step.is_complete() is True


@pytest.mark.django_db
def test_existing_superuser_stamps_flag_and_step_never_reopens():
    """A DB that already has a superuser closes the step for good on the first
    check — deleting every superuser later must not re-open it."""
    from first_run_wizard.builtin_steps import AdminUserCreationStep
    from first_run_wizard.models import FirstRunWizardState

    User.objects.create_superuser(username="root", email="r@example.com", password="r")  # noqa: S106
    assert FirstRunWizardState.load().admin_created_at is None
    assert AdminUserCreationStep().is_complete() is True
    assert FirstRunWizardState.load().admin_created_at is not None

    User.objects.all().delete()
    assert AdminUserCreationStep().is_complete() is True


@pytest.mark.django_db
def test_wizard_asks_for_admin_when_only_ordinary_users_exist():
    """Fresh install with a non-superuser account (inactive technical account)
    — the wizard still redirects to the admin step and creates the admin."""
    User.objects.create_user(username="bpp-system", is_active=False)
    client = Client()
    response = client.get("/")
    url = reverse("first_run_wizard:step", kwargs={"name": "admin_user"})
    assert response.status_code == 302
    assert response.url == url
    response = client.post(
        url,
        {
            "username": "admin",
            "email": "admin@example.com",
            "password1": "Very-Long-Unique-Passphrase-7a",
            "password2": "Very-Long-Unique-Passphrase-7a",
        },
    )
    assert response.status_code == 302
    assert User.objects.get(username="admin").is_superuser


@pytest.mark.django_db
def test_admin_step_rejects_username_of_an_ordinary_user():
    User.objects.create_user(username="taken", password="x")  # noqa: S106
    url = reverse("first_run_wizard:step", kwargs={"name": "admin_user"})
    response = Client().post(
        url,
        {
            "username": "taken",
            "email": "admin@example.com",
            "password1": "Very-Long-Unique-Passphrase-7a",
            "password2": "Very-Long-Unique-Passphrase-7a",
        },
    )
    assert response.status_code == 200
    assert "username" in response.context["form"].errors
    assert not User.objects.filter(is_superuser=True).exists()


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
def test_admin_step_rejects_password_too_short():
    """Validators from settings must apply (same as admin / createsuperuser)."""
    client = Client()
    url = reverse("first_run_wizard:step", kwargs={"name": "admin_user"})
    response = client.post(
        url,
        {
            "username": "rootadmin",
            "email": "root@example.com",
            "password1": "short1",
            "password2": "short1",
        },
    )
    assert response.status_code == 200, (
        "form should re-render with errors, not redirect"
    )
    assert User.objects.count() == 0
    form = response.context["form"]
    assert form.errors, "form should have errors"
    assert "password1" in form.errors
    joined = " ".join(form.errors["password1"]).lower()
    assert "too short" in joined or "8 char" in joined


@pytest.mark.django_db
def test_admin_step_rejects_password_equal_to_username():
    """UserAttributeSimilarityValidator must reject password == username."""
    client = Client()
    url = reverse("first_run_wizard:step", kwargs={"name": "admin_user"})
    response = client.post(
        url,
        {
            "username": "rootadmin",
            "email": "root@example.com",
            "password1": "rootadmin",
            "password2": "rootadmin",
        },
    )
    assert response.status_code == 200, (
        "form should re-render with errors, not redirect"
    )
    assert User.objects.count() == 0
    form = response.context["form"]
    assert form.errors, "form should have errors"
    assert "password1" in form.errors
    joined = " ".join(form.errors["password1"]).lower()
    assert "similar" in joined or "username" in joined


@pytest.mark.django_db
def test_admin_step_rejects_when_superuser_already_exists():
    User.objects.create_superuser(
        username="existing",
        email="e@example.com",
        password="x",  # noqa: S106
    )
    client = Client()
    url = reverse("first_run_wizard:step", kwargs={"name": "admin_user"})
    response = client.get(url)
    # A superuser exists → admin_user is the only builtin step and it's complete →
    # the whole wizard is complete. The middleware's repair path stamps
    # completed_at on construction, so /setup/ is closed for good: 404, not a
    # redirect. (A second admin can never be created here again.)
    assert response.status_code == 404


@pytest.mark.django_db
def test_status_view_lists_steps():
    url = reverse("first_run_wizard:status")
    response = Client().get(url)
    # The middleware should let /setup/ through (it's the wizard area).
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "admin" in body.lower()
