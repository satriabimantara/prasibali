"""Login, logout, password reset and allauth's built-in login rate limit."""

import re

import pytest
from allauth.account import app_settings as allauth_settings
from django.core import mail
from django.urls import reverse

NEW_PASSWORD = "Lontar-Prasi-9090!"  # throwaway test value


def login(client, email, password):
    return client.post(reverse("account_login"), {"login": email, "password": password})


def test_login_url_is_indonesian():
    assert reverse("account_login") == "/masuk/"


@pytest.mark.django_db
def test_login_page_follows_design(client):
    html = client.get(reverse("account_login")).content.decode()

    assert "Masuk ke akun Anda" in html
    assert 'autocomplete="email"' in html
    assert 'autocomplete="current-password"' in html
    assert reverse("account_signup") in html


@pytest.mark.django_db
def test_wrong_password_is_rejected(client, verified_user):
    response = login(client, verified_user.email, "wrong-password")

    assert response.status_code == 200
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_logout_requires_post(client, verified_user, password):
    login(client, verified_user.email, password)

    assert client.get(reverse("account_logout")).status_code == 200  # confirmation page only
    assert "_auth_user_id" in client.session

    response = client.post(reverse("account_logout"))
    assert response.status_code == 302
    assert response["Location"] == reverse("pages:landing")
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_password_reset(client, verified_user, password):
    response = client.post(reverse("account_reset_password"), {"email": verified_user.email})
    assert response.status_code == 302
    assert len(mail.outbox) == 1

    path = re.search(r"https?://[^/\s]+(/akun/password/reset/key/[^\s]+/)", mail.outbox[0].body).group(1)
    response = client.get(path)
    assert response.status_code == 302  # allauth moves the key into the session
    set_password_url = response["Location"]

    response = client.post(set_password_url, {"password1": NEW_PASSWORD, "password2": NEW_PASSWORD})
    assert response.status_code == 302

    client.cookies.clear()
    assert login(client, verified_user.email, password).status_code == 200  # old password no longer works
    assert login(client, verified_user.email, NEW_PASSWORD).status_code == 302
    assert "_auth_user_id" in client.session


def _failed_login_limit_per_key():
    """Read the per-account limit from allauth's own defaults, e.g. '10/m/ip,5/300s/key' -> 5."""
    for rule in allauth_settings.RATE_LIMITS["login_failed"].split(","):
        if rule.endswith("/key"):
            return int(rule.split("/")[0])
    raise AssertionError("allauth has no per-key login_failed rate limit")


@pytest.mark.django_db
def test_failed_logins_are_rate_limited(client, verified_user, password):
    for _ in range(_failed_login_limit_per_key()):
        login(client, verified_user.email, "wrong-password")

    response = login(client, verified_user.email, password)

    assert response.status_code == 200
    assert "_auth_user_id" not in client.session
    assert response.context["form"].errors
