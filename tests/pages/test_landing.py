import pytest
from django.urls import reverse

FOOTER = "Copyright 2026 | I Made Satria Bimantara, S.Kom., M.Kom."


@pytest.mark.django_db
def test_landing_for_visitors(client):
    response = client.get("/")
    html = response.content.decode()

    assert response.status_code == 200
    assert "img/prasibali-logo-latar-terang" in html and "img/prasibali-logo-latar-gelap" in html
    assert "&#x1B27;&#x1B44;&#x1B2D;&#x1B32;&#x1B36;" in html
    assert "Analisis tokoh satua Bali dalam satu ruang kerja." in html
    assert f'action="{reverse("account_login")}"' in html and 'name="password"' in html
    assert f'href="{reverse("account_signup")}"' in html
    assert "Kenali tokoh" in html and "Satukan nama lain" in html and "Lihat perannya" in html
    assert FOOTER in html


@pytest.mark.django_db
def test_landing_for_signed_in_user(client, verified_user):
    client.force_login(verified_user)
    html = client.get("/").content.decode()

    assert f'href="{reverse("analysis:workspace")}"' in html
    assert 'name="password"' not in html
    assert f'action="{reverse("account_logout")}"' in html


@pytest.mark.django_db
def test_logout_redirects_to_landing(client, verified_user):
    client.force_login(verified_user)
    response = client.post(reverse("account_logout"))
    assert response.status_code == 302 and response["Location"] == reverse("pages:landing")


@pytest.mark.django_db
def test_navbar_auth_buttons(client, verified_user):
    html = client.get(reverse("pages:privacy")).content.decode()
    assert "Masuk" in html and "Daftar" in html and FOOTER in html
    assert "<svg" in html  # icons next to the button labels

    client.force_login(verified_user)
    html = client.get(reverse("pages:privacy")).content.decode()
    assert "Keluar" in html and "Profil" in html and f'href="{reverse("analysis:workspace")}"' in html


@pytest.mark.django_db
def test_login_page_has_logo_and_footer(client):
    html = client.get(reverse("account_login")).content.decode()
    assert "img/prasibali-logo-latar-terang" in html and FOOTER in html
