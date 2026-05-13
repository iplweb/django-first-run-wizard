"""Verify that the bundled Polish translation actually activates."""

from __future__ import annotations

from django.utils.translation import gettext as _
from django.utils.translation import override

from first_run_wizard.builtin_steps.admin_user import (
    AdminUserCreationForm,
    AdminUserCreationStep,
)


def test_polish_translation_loads_for_form_labels():
    with override("pl"):
        form = AdminUserCreationForm()
        assert form.fields["username"].label == "Nazwa użytkownika"
        assert form.fields["email"].label == "Adres e-mail"
        assert form.fields["password1"].label == "Hasło"
        assert form.fields["password2"].label == "Potwierdzenie hasła"


def test_polish_translation_loads_for_step_verbose_name():
    with override("pl"):
        assert (
            str(AdminUserCreationStep().verbose_name) == "Utwórz konto administratora"
        )


def test_polish_translation_loads_for_template_strings():
    with override("pl"):
        assert _("First-Run Wizard") == "Kreator pierwszego uruchomienia"
        assert _("Setup status") == "Stan konfiguracji"
        assert _("Create administrator") == "Utwórz administratora"


def test_english_remains_default_when_no_override():
    form = AdminUserCreationForm()
    assert str(form.fields["username"].label) == "Username"
