"""Profile editing, preferred language, and account deletion."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


def login(client, email, password):
    return client.post(reverse("account_login"), {"login": email, "password": password})


@pytest.mark.django_db
def test_profile_requires_login(client):
    response = client.get(reverse("accounts:profile"))

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("account_login"))


@pytest.mark.django_db
def test_update_profile(client, verified_user, password):
    login(client, verified_user.email, password)
    response = client.post(
        reverse("accounts:profile"),
        {"full_name": "Ketut Lontar", "institution": "SMA 1 Denpasar", "role": "teacher", "language": "en"},
    )

    assert response.status_code == 302
    verified_user.refresh_from_db()
    assert verified_user.full_name == "Ketut Lontar"
    assert verified_user.institution == "SMA 1 Denpasar"
    assert verified_user.role == "teacher"
    assert verified_user.language == "en"
    assert response.cookies["django_language"].value == "en"


@pytest.mark.django_db
def test_profile_requires_full_name(client, verified_user, password):
    login(client, verified_user.email, password)
    response = client.post(
        reverse("accounts:profile"), {"full_name": "", "institution": "", "role": "general", "language": "id"}
    )

    assert response.status_code == 200
    assert "full_name" in response.context["form"].errors


@pytest.mark.django_db
def test_preferred_language_is_used_after_login(client, make_user, password):
    user = make_user(language="en")
    login(client, user.email, password)
    response = client.get(reverse("accounts:profile"))

    assert response["Content-Language"] == "en"
    assert "Save profile" in response.content.decode()


@pytest.mark.django_db
def test_indonesian_is_the_default_language(client, verified_user, password):
    login(client, verified_user.email, password)
    response = client.get(reverse("accounts:profile"))

    assert response["Content-Language"] == "id"
    assert "Simpan profil" in response.content.decode()


@pytest.mark.django_db
def test_language_switch_updates_profile(client, verified_user, password):
    login(client, verified_user.email, password)
    response = client.post(reverse("accounts:set_language"), {"language": "en", "next": "/akun/profil/"})

    assert response.status_code == 302
    verified_user.refresh_from_db()
    assert verified_user.language == "en"


@pytest.mark.django_db
def test_language_switch_for_anonymous_visitors(client):
    response = client.post(reverse("accounts:set_language"), {"language": "en", "next": "/daftar/"})

    assert response.cookies["django_language"].value == "en"
    assert "Create a new account" in client.get(reverse("account_signup")).content.decode()


@pytest.mark.django_db
def test_delete_account_with_wrong_password_is_refused(client, verified_user, password):
    login(client, verified_user.email, password)
    response = client.post(reverse("accounts:delete"), {"password": "wrong-password"})

    assert response.status_code == 200
    assert response.context["form"].errors["password"]
    assert get_user_model().objects.filter(pk=verified_user.pk).exists()


@pytest.mark.django_db
def test_delete_account(client, verified_user, password):
    login(client, verified_user.email, password)
    response = client.post(reverse("accounts:delete"), {"password": password})

    assert response.status_code == 302
    assert response["Location"] == reverse("account_login")
    assert not get_user_model().objects.filter(pk=verified_user.pk).exists()
    assert "_auth_user_id" not in client.session
