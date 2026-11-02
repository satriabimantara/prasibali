from allauth.account.forms import SignupForm as AllauthSignupForm
from django import forms
from django.conf import settings
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _

from .models import PRIVACY_POLICY_VERSION, User

SIGNUP_FIELD_ORDER = [
    "email",
    "full_name",
    "institution",
    "role",
    "password1",
    "password2",
    "language",
    "accept_privacy",
]


def _initial_language():
    active = translation.get_language() or settings.LANGUAGE_CODE
    codes = [code for code, _name in settings.LANGUAGES]
    return active if active in codes else settings.LANGUAGE_CODE


class SignupForm(AllauthSignupForm):
    """allauth signup plus the profile fields and the privacy policy consent."""

    full_name = forms.CharField(
        label=_("Full name"),
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
    )
    institution = forms.CharField(
        label=_("Institution"),
        max_length=200,
        required=False,
        help_text=_("School, university, or organisation. Optional."),
        widget=forms.TextInput(attrs={"autocomplete": "organization"}),
    )
    role = forms.ChoiceField(label=_("I am a"), choices=[("", _("Choose your role")), *User.Role.choices])
    language = forms.ChoiceField(label=_("Interface language"), choices=settings.LANGUAGES)
    accept_privacy = forms.BooleanField(
        label=_("I have read and agree to the privacy policy."),
        error_messages={"required": _("Agree to the privacy policy to create an account.")},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["language"].initial = _initial_language()
        self.order_fields(SIGNUP_FIELD_ORDER)

    def custom_signup(self, request, user):
        data = self.cleaned_data
        user.full_name = data["full_name"].strip()
        user.institution = data.get("institution", "").strip()
        user.role = data["role"]
        user.language = data["language"]
        user.privacy_accepted_at = timezone.now()
        user.privacy_policy_version = PRIVACY_POLICY_VERSION
        user.save(
            update_fields=[
                "full_name",
                "institution",
                "role",
                "language",
                "privacy_accepted_at",
                "privacy_policy_version",
            ]
        )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name", "institution", "role", "language"]
        labels = {
            "full_name": _("Full name"),
            "institution": _("Institution"),
            "role": _("I am a"),
            "language": _("Interface language"),
        }
        help_texts = {"institution": _("School, university, or organisation. Optional.")}
        widgets = {
            "full_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "institution": forms.TextInput(attrs={"autocomplete": "organization"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["full_name"].required = True


class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError(_("The password is incorrect."))
        return password
