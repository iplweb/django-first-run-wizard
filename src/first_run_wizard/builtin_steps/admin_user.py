"""Built-in step: create the very first admin user."""

from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model, login, password_validation
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from first_run_wizard.exceptions import SetupAlreadyClaimed
from first_run_wizard.models import FirstRunWizardState
from first_run_wizard.steps import SetupStep

__all__ = [
    "AdminUserCreationForm",
    "AdminUserCreationStep",
    "SetupAlreadyClaimed",
    "create_first_admin",
]


def create_first_admin(*, username, email, password):
    """Create the first superuser under a row lock, or refuse.

    The singleton state row is locked with ``select_for_update`` so two
    concurrent POSTs serialize here. The winner re-checks — *after*
    acquiring the lock — that no admin exists yet, creates the superuser,
    and stamps ``admin_created_at``. The loser sees the stamp (or the
    freshly-created user) and raises :class:`SetupAlreadyClaimed`.

    The post-lock re-check, not the form's ``clean()``, is the security
    boundary: ``clean()`` runs before the lock and only drives a friendly
    message.
    """
    User = get_user_model()
    with transaction.atomic():
        FirstRunWizardState.objects.get_or_create(pk=1)
        state = FirstRunWizardState.objects.select_for_update().get(pk=1)
        if state.admin_created_at or User.objects.exists():
            raise SetupAlreadyClaimed
        user = User.objects.create_superuser(
            username=username, email=email, password=password
        )
        state.admin_created_at = timezone.now()
        state.save(update_fields=["admin_created_at"])
    return user


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
            # Build an UNSAVED user instance so UserAttributeSimilarityValidator
            # can compare the password against username/email/first/last name
            # — same contract as django.contrib.auth.forms.UserCreationForm and
            # the createsuperuser management command.
            User = get_user_model()
            user_attrs = {}
            for field in ("username", "email", "first_name", "last_name"):
                value = cleaned.get(field)
                if value and hasattr(User, field):
                    user_attrs[field] = value
            unsaved_user = User(**user_attrs) if user_attrs else None
            try:
                password_validation.validate_password(p1, unsaved_user)
            except ValidationError as e:
                self.add_error("password1", e)
        return cleaned

    def save(self):
        # Delegate to the locked helper — it may raise SetupAlreadyClaimed,
        # which the step view turns into a form error (not a 500).
        return create_first_admin(
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
