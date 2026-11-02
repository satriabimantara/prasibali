import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command

DEMO_EMAIL = "demo@example.com"


@pytest.mark.django_db
def test_create_demo_user_is_idempotent(monkeypatch, client):
    monkeypatch.setenv("DEMO_USER_EMAIL", DEMO_EMAIL)
    monkeypatch.setenv("DEMO_USER_PASSWORD", "first-Demo-pass-1")
    call_command("create_demo_user")

    monkeypatch.setenv("DEMO_USER_PASSWORD", "second-Demo-pass-2")
    call_command("create_demo_user")

    user = get_user_model().objects.get(email=DEMO_EMAIL)
    assert get_user_model().objects.count() == 1
    assert user.check_password("second-Demo-pass-2")
    assert user.privacy_accepted_at is not None
    address = EmailAddress.objects.get(user=user)
    assert address.verified and address.primary

    response = client.post("/masuk/", {"login": DEMO_EMAIL, "password": "second-Demo-pass-2"})
    assert response.status_code == 302
    assert "_auth_user_id" in client.session


@pytest.mark.django_db
def test_create_demo_user_needs_env(monkeypatch):
    monkeypatch.delenv("DEMO_USER_EMAIL", raising=False)
    monkeypatch.delenv("DEMO_USER_PASSWORD", raising=False)

    with pytest.raises(CommandError, match="DEMO_USER_EMAIL"):
        call_command("create_demo_user")
