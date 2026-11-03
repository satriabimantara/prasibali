"""Account settings page: interface language (stored on the profile) and theme (session 5)."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_settings_requires_login(client):
    response = client.get(reverse("accounts:settings"))
    assert response.status_code == 302
    assert response["Location"].startswith(reverse("account_login"))


@pytest.mark.django_db
def test_settings_page(client, verified_user):
    client.force_login(verified_user)
    html = client.get(reverse("accounts:settings")).content.decode()

    assert f'action="{reverse("accounts:set_language")}"' in html
    assert 'name="language" value="id" checked' in html
    assert 'data-theme-set="dark"' in html and 'data-theme-set="light"' in html


@pytest.mark.django_db
def test_settings_language_is_saved_to_profile(client, verified_user):
    client.force_login(verified_user)
    url = reverse("accounts:settings")
    response = client.post(reverse("accounts:set_language"), {"language": "en", "next": url})

    assert response.status_code == 302 and response["Location"] == url
    verified_user.refresh_from_db()
    assert verified_user.language == "en"
    html = client.get(url).content.decode()
    assert "Settings" in html and 'name="language" value="en" checked' in html
