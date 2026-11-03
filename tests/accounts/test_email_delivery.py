"""Transactional emails (Hostinger Email SMTP in production; locmem backend here).

Every email the app sends goes out from DEFAULT_FROM_EMAIL (the noreply@prasibali.tech mailbox, which must match
EMAIL_HOST_USER) and links back over https to the host the user visited.
"""

import importlib
import re
import sys

import pytest
from django.conf import settings
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from django.urls import reverse
from test_signup_flow import signup_data

FROM = "PrasiBali.ai <noreply@prasibali.tech>"
HTTPS = {"ACCOUNT_DEFAULT_HTTP_PROTOCOL": "https", "DEFAULT_FROM_EMAIL": FROM}


def links(message):
    return re.findall(r"https?://[^\s]+", message.body)


def test_email_defaults_point_to_hostinger(monkeypatch):
    """Code defaults (no .env, no EMAIL_* variables): Hostinger SMTP on 587 with STARTTLS, noreply sender."""
    import environ

    monkeypatch.setattr(environ.Env, "read_env", classmethod(lambda cls, *args, **kwargs: None))
    for name in ("EMAIL_HOST", "EMAIL_PORT", "EMAIL_USE_TLS", "EMAIL_USE_SSL", "EMAIL_TIMEOUT", "DEFAULT_FROM_EMAIL",
                 "SERVER_EMAIL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DJANGO_SECRET_KEY", "test-only-not-a-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite://:memory:")
    sys.modules.pop("config.settings.base", None)
    try:
        base = importlib.import_module("config.settings.base")
        assert base.EMAIL_HOST == "smtp.hostinger.com"
        assert base.EMAIL_PORT == 587 and base.EMAIL_USE_TLS and not base.EMAIL_USE_SSL
        assert base.EMAIL_TIMEOUT == 20
        assert base.DEFAULT_FROM_EMAIL == base.SERVER_EMAIL == FROM
    finally:
        sys.modules.pop("config.settings.base", None)


def test_active_settings_use_a_single_encryption_mode():
    assert not (settings.EMAIL_USE_TLS and settings.EMAIL_USE_SSL)
    assert settings.EMAIL_TIMEOUT > 0


@pytest.mark.django_db
@override_settings(**HTTPS)
def test_signup_verification_email(client, password):
    client.post(reverse("account_signup"), signup_data(password))
    message = mail.outbox[-1]
    assert message.from_email == FROM
    assert message.to == ["made.bhaskara@example.com"]
    assert any("/akun/confirm-email/" in url and url.startswith("https://testserver/") for url in links(message))


@pytest.mark.django_db
@override_settings(**HTTPS)
def test_password_reset_email(client, verified_user):
    client.post(reverse("account_reset_password"), {"email": verified_user.email})
    message = mail.outbox[-1]
    assert message.from_email == FROM and message.to == [verified_user.email]
    assert any("/akun/password/reset/key/" in url and url.startswith("https://") for url in links(message))


@pytest.mark.django_db
@override_settings(**HTTPS)
def test_adding_an_email_address_sends_a_confirmation(client, verified_user):
    client.force_login(verified_user)
    response = client.post(reverse("account_email"), {"action_add": "", "email": "baru@example.com"})
    assert response.status_code == 302
    message = mail.outbox[-1]
    assert message.from_email == FROM and message.to == ["baru@example.com"]
    assert any("/akun/confirm-email/" in url for url in links(message))


@pytest.mark.django_db
def test_profile_update_sends_no_email(client, verified_user):
    client.force_login(verified_user)
    client.post(reverse("accounts:profile"), {"full_name": "Ketut Lontar", "institution": "", "role": "general"})
    assert mail.outbox == []


def test_prod_refuses_tls_and_ssl_together(monkeypatch):
    for name, value in {
        "DJANGO_SECRET_KEY": "test-only-not-a-secret", "DJANGO_ALLOWED_HOSTS": "prasibali.tech",
        "CSRF_TRUSTED_ORIGINS": "https://prasibali.tech", "DATABASE_URL": "sqlite://:memory:",
        "EMAIL_USE_TLS": "true", "EMAIL_USE_SSL": "true",
    }.items():
        monkeypatch.setenv(name, value)
    for module in ("config.settings.prod", "config.settings.base"):
        sys.modules.pop(module, None)
    try:
        with pytest.raises(ImproperlyConfigured):
            importlib.import_module("config.settings.prod")
    finally:
        for module in ("config.settings.prod", "config.settings.base"):
            sys.modules.pop(module, None)
        monkeypatch.undo()
        importlib.import_module("config.settings.base")  # restore the module for later imports
