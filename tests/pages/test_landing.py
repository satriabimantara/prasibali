import re

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
    # Problem, solution, three steps and the call to action (session 5); no sign-in form any more.
    assert 'id="masalah"' in html and 'id="solusi"' in html and 'id="cara-kerja"' in html
    assert "Identifikasi tokoh" in html and "Alias clustering" in html and "Klasifikasi peran" in html
    assert html.count('class="step-number"') == 3
    assert "Mulai analisis" in html and f'href="{reverse("analysis:workspace")}"' in html
    assert f'href="{reverse("account_signup")}"' in html and f'href="{reverse("account_login")}"' in html
    assert 'name="password"' not in html
    assert "Contoh tampilan hasil" in html
    assert FOOTER in html


@pytest.mark.django_db
def test_landing_for_signed_in_user(client, verified_user):
    client.force_login(verified_user)
    html = client.get("/").content.decode()

    assert "Lanjutkan ke ruang kerja" in html
    assert f'href="{reverse("analysis:history")}"' in html
    assert f'action="{reverse("account_logout")}"' in html
    assert f'href="{reverse("account_signup")}"' not in html


@pytest.mark.django_db
def test_logout_redirects_to_landing(client, verified_user):
    client.force_login(verified_user)
    response = client.post(reverse("account_logout"))
    assert response.status_code == 302 and response["Location"] == reverse("pages:landing")


@pytest.mark.django_db
def test_login_page_has_logo_and_footer(client):
    html = client.get(reverse("account_login")).content.decode()
    assert "img/prasibali-logo-latar-terang" in html and FOOTER in html


@pytest.mark.django_db
def test_landing_in_english(client):
    client.cookies["django_language"] = "en"
    html = client.get("/").content.decode()
    assert "Character analysis of Balinese satua in one workspace." in html
    assert "How it works in three steps" in html and "Start analysing" in html


@pytest.mark.django_db
@pytest.mark.parametrize("language", ["id", "en"])
@pytest.mark.parametrize(
    "url_name", ["pages:landing", "pages:about", "pages:privacy", "account_login", "account_signup"]
)
def test_product_name_is_prasibali_without_suffix(client, language, url_name):
    """The product is called "PrasiBali" everywhere; no ".ai" (or other domain) suffix in titles or text."""
    client.cookies["django_language"] = language
    html = client.get(reverse(url_name)).content.decode()
    title = re.search(r"<title>(.*?)</title>", html, re.S).group(1)
    assert "PrasiBali" in title and ".ai" not in title
    assert "PrasiBali.ai" not in html
