"""Site navbar (session 5): features dropdown, account menu, mobile menu and keyboard support hooks."""

import pytest
from django.urls import reverse

from apps.pages.features import AVAILABLE_FEATURES, COMING_SOON_FEATURES, FEATURES


def test_feature_registry():
    assert len(AVAILABLE_FEATURES) == 3 and len(COMING_SOON_FEATURES) == 5
    assert [f.slug for f in COMING_SOON_FEATURES] == [
        "coreference", "social-graph", "quote-attribution", "summarization", "aksara-bali",
    ]
    assert len({f.slug for f in FEATURES}) == len(FEATURES)


@pytest.mark.django_db
def test_navbar_for_visitors(client):
    html = client.get(reverse("pages:privacy")).content.decode()

    assert 'class="skip-link" href="#main"' in html and 'id="main"' in html
    assert 'aria-controls="features-menu"' in html and 'aria-expanded="false"' in html
    assert 'aria-controls="mobile-menu"' in html
    for feature in FEATURES:
        assert f'href="{feature.url}"' in html
    # Five "coming soon" badges in the desktop dropdown and five in the mobile menu.
    assert html.count('<span class="tag">Segera hadir</span>') == 10
    assert f'href="{reverse("pages:about")}"' in html
    assert "Masuk" in html and "Daftar" in html and "<svg" in html
    assert f'action="{reverse("accounts:set_language")}"' in html  # visitors keep the language switch
    assert 'aria-controls="account-menu"' not in html


@pytest.mark.django_db
def test_navbar_for_signed_in_user(client, verified_user):
    client.force_login(verified_user)
    html = client.get(reverse("pages:privacy")).content.decode()

    assert 'aria-controls="account-menu"' in html
    assert f'href="{reverse("accounts:profile")}"' in html
    assert f'href="{reverse("analysis:history")}"' in html
    assert f'href="{reverse("accounts:settings")}"' in html and "Pengaturan" in html
    assert f'action="{reverse("account_logout")}" method="post"' in html and "Keluar" in html
    assert f'href="{reverse("account_login")}"' not in html


@pytest.mark.django_db
def test_navbar_marks_current_page(client):
    html = client.get(reverse("pages:about")).content.decode()
    assert f'href="{reverse("pages:about")}" aria-current="page"' in html


@pytest.mark.django_db
def test_sign_in_page_hides_auth_links_but_keeps_language(client):
    html = client.get(reverse("account_login")).content.decode()
    assert f'href="{reverse("account_signup")}" ' not in html.split("</header>")[0]
    assert f'action="{reverse("accounts:set_language")}"' in html
