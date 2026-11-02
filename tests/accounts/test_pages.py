import pytest
from django.urls import reverse

from apps.accounts.models import PRIVACY_POLICY_VERSION


@pytest.mark.django_db
def test_privacy_page(client):
    response = client.get(reverse("pages:privacy"))

    assert response.status_code == 200
    html = response.content.decode()
    assert "Kebijakan privasi" in html
    assert PRIVACY_POLICY_VERSION in html


@pytest.mark.django_db
def test_signup_page_links_to_privacy_policy(client):
    html = client.get(reverse("account_signup")).content.decode()

    assert f'href="{reverse("pages:privacy")}"' in html


@pytest.mark.django_db
def test_signup_page_in_english_with_language_cookie(client):
    """Proves the compiled translations (.mo) are present: Indonesian by default, English on request."""
    assert "Buat akun baru" in client.get(reverse("account_signup")).content.decode()

    client.cookies["django_language"] = "en"
    response = client.get(reverse("account_signup"))
    assert response["Content-Language"] == "en"
    assert "Create a new account" in response.content.decode()
