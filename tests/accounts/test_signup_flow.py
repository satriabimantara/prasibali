"""Core account flow: sign up -> verify email -> sign in (allauth with mandatory verification)."""

import re

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse

from apps.accounts.models import PRIVACY_POLICY_VERSION

EMAIL = "Made.Bhaskara@Example.com"


def signup_data(password, **overrides):
    data = {
        "email": EMAIL,
        "full_name": "Made Bhaskara",
        "institution": "Universitas Udayana",
        "role": "researcher",
        "password1": password,
        "password2": password,
        "language": "id",
        "accept_privacy": "on",
    }
    data.update(overrides)
    return data


def confirmation_url(message_body):
    match = re.search(r"https?://[^/\s]+(/akun/confirm-email/[^\s]+/)", message_body)
    assert match, message_body
    return match.group(1)


def login(client, email, password):
    return client.post(reverse("account_login"), {"login": email, "password": password})


@pytest.mark.django_db
def test_signup_verify_login(client, password):
    # 1. The signup page follows DESIGN.md: Prasi script and ikat ribbon on the card.
    page = client.get(reverse("account_signup"))
    assert page.status_code == 200
    html = page.content.decode()
    assert "ᬧ᭄ᬭᬲᬶ" in html or "&#x1B27;" in html
    assert "h-[132px]" in html
    assert reverse("account_signup") == "/daftar/"

    # 2. Sign up: the account exists with its profile, but nobody is signed in yet.
    response = client.post(reverse("account_signup"), signup_data(password))
    assert response.status_code == 302
    assert response["Location"] == reverse("account_email_verification_sent")
    assert "_auth_user_id" not in client.session

    user = get_user_model().objects.get(email=EMAIL.lower())
    assert user.full_name == "Made Bhaskara"
    assert user.institution == "Universitas Udayana"
    assert user.role == "researcher"
    assert user.language == "id"
    assert user.privacy_accepted_at is not None
    assert user.privacy_policy_version == PRIVACY_POLICY_VERSION
    assert EmailAddress.objects.get(user=user).verified is False

    # 3. One verification email with a confirmation link.
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [EMAIL.lower()]
    assert mail.outbox[0].subject.startswith("[PrasiBali.ai]")
    url = confirmation_url(mail.outbox[0].body)

    # 4. Signing in before verification is refused.
    client.cookies.clear()
    response = login(client, EMAIL, password)
    assert response.status_code == 302
    assert response["Location"] == reverse("account_email_verification_sent")
    assert "_auth_user_id" not in client.session

    # 5. Opening the link does not confirm by itself (no confirmation on GET); the POST does.
    assert client.get(url).status_code == 200
    assert EmailAddress.objects.get(user=user).verified is False
    response = client.post(url)
    assert response.status_code == 302
    assert EmailAddress.objects.get(user=user).verified is True

    # 6. Now the login works and lands on the profile page.
    response = login(client, EMAIL, password)
    assert response.status_code == 302
    assert response["Location"] == reverse("accounts:profile")
    assert int(client.session["_auth_user_id"]) == user.pk
    assert client.get(reverse("accounts:profile")).status_code == 200


@pytest.mark.django_db
def test_signup_without_privacy_consent_is_rejected(client, password):
    data = signup_data(password)
    del data["accept_privacy"]
    response = client.post(reverse("account_signup"), data)

    assert response.status_code == 200
    assert response.context["form"].errors["accept_privacy"]
    assert 'aria-invalid="true"' in response.content.decode()
    assert not get_user_model().objects.exists()
    assert mail.outbox == []


@pytest.mark.django_db
@pytest.mark.parametrize("field", ["full_name", "role", "email"])
def test_signup_requires_profile_fields(client, password, field):
    response = client.post(reverse("account_signup"), signup_data(password, **{field: ""}))

    assert response.status_code == 200
    assert field in response.context["form"].errors
    assert not get_user_model().objects.exists()


@pytest.mark.django_db
def test_institution_is_optional(client, password):
    client.post(reverse("account_signup"), signup_data(password, institution=""))

    assert get_user_model().objects.get(email=EMAIL.lower()).institution == ""


@pytest.mark.django_db
def test_duplicate_email_does_not_create_second_account(client, password, make_user):
    make_user(email=EMAIL.lower())
    client.post(reverse("account_signup"), signup_data(password))

    assert get_user_model().objects.filter(email__iexact=EMAIL).count() == 1
