"""Feature pages (/fitur/<slug>/) and the about page (session 5)."""

import pytest
from django.urls import reverse

from apps.analysis.services import model_catalog as mc
from apps.pages.features import AVAILABLE_FEATURES, COMING_SOON_FEATURES, FEATURES


@pytest.mark.django_db
@pytest.mark.parametrize("feature", FEATURES, ids=lambda f: f.slug)
def test_every_feature_page_renders(client, feature):
    response = client.get(feature.url)
    assert response.status_code == 200
    assert str(feature.title) in response.content.decode()


@pytest.mark.django_db
def test_unknown_feature_is_404(client):
    assert client.get(reverse("pages:feature", args=["tidak-ada"])).status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("feature", AVAILABLE_FEATURES, ids=lambda f: f.slug)
def test_available_feature_links_to_workspace_task(client, feature):
    html = client.get(feature.url).content.decode()
    assert feature.task in mc.TASKS
    assert f'href="{reverse("analysis:workspace")}?tugas={feature.task}"' in html


@pytest.mark.django_db
@pytest.mark.parametrize("feature", COMING_SOON_FEATURES, ids=lambda f: f.slug)
def test_coming_soon_feature_has_no_workspace_link(client, feature):
    html = client.get(feature.url).content.decode()
    assert "?tugas=" not in html
    assert "Segera hadir" in html


@pytest.mark.django_db
def test_role_feature_reads_models_from_the_catalog(client):
    html = client.get(reverse("pages:feature", args=["klasifikasi-peran"])).content.decode()
    default = mc.get_classifier_entry(mc.DEFAULT_CLASSIFIER_ID, require_available=False)
    best = mc.get_classifier_entry(mc.THESIS_BEST_CLASSIFIER_ID, require_available=False)
    assert f"{default.algorithm} + {default.feature_label} (M2)" in html
    assert f"{best.algorithm} + {best.feature_label} (M2)" in html
    assert "0,6811" in html  # Indonesian number format
    assert "di bawah 0,70" in html  # disclaimer


@pytest.mark.django_db
def test_about_page(client):
    html = client.get(reverse("pages:about")).content.decode()
    assert "I Made Satria Bimantara, S.Kom., M.Kom." in html
    assert "Dr. Ir. Ngurah Agus Sanjaya ER, S.Kom., M.Kom." in html
    assert "Prof. Dr. Ir. Diana Purwitasari, S.Kom., M.Sc." in html
    assert 'href="https://doi.org/10.1007/978-3-031-48316-5_15" rel="noopener"' in html
    assert "Balinese Story Texts Dataset for Narrative Text Analyses" in html
    assert "https://pypi.org/project/balinese-nlp/2.4.2/" in html


@pytest.mark.django_db
def test_about_page_in_english(client):
    client.cookies["django_language"] = "en"
    html = client.get(reverse("pages:about")).content.decode()
    assert "About PrasiBali.ai" in html and "Team lead" in html
