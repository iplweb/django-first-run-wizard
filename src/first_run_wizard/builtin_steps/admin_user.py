"""Built-in step: create the very first admin user."""

from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model, login, password_validation
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from first_run_wizard.steps import SetupStep


class AdminUserCreationForm(forms.Form):
    """Create the first superuser on a fresh install.

    Plain `forms.Form` (not `ModelForm`) so it stays decoupled from the
    project's `AUTH_USER_MODEL`. Uses `User.objects.create_superuser()`,
    which is the swappable-user-model contract every custom User manager
    must support.
    """

    username = forms.CharField(
        max_length=150,
        label=_("Username"),
        help_text=_(
            "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        ),
    )
    email = forms.EmailField(
        label=_("Email address"),
        help_text=_("Required. Used for password reset and admin notices."),
    )
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput,
        strip=False,
    )
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput,
        strip=False,
        help_text=_("Enter the same password as before, for verification."),
    )

    def clean(self):
        cleaned = super().clean()
        if get_user_model().objects.exists():
            raise ValidationError(
                _("The setup wizard can only run on an empty user table.")
            )

        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error(
                "password2",
                ValidationError(
                    _("The two password fields didn't match."),
                    code="password_mismatch",
                ),
            )
        if p1:
            try:
                password_validation.validate_password(p1)
            except ValidationError as e:
                self.add_error("password1", e)
        return cleaned

    def save(self):
        User = get_user_model()
        return User.objects.create_superuser(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"],
        )


class AdminUserCreationStep(SetupStep):
    name = "admin_user"
    verbose_name = _("Create the administrator account")
    order = 0
    form_class = AdminUserCreationForm
    template_name = "first_run_wizard/admin_user.html"
    requires_authentication = False
    requires_superuser = False

    def is_complete(self) -> bool:
        return get_user_model().objects.exists()

    def on_complete(self, form, request):
        user = form.save()
        login(
            request,
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        return user
