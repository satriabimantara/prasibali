"""Analysis workspace view. The pipeline is replaced by a fake result, so no models are loaded (runs in CI)."""

import pytest
from django.urls import reverse

from apps.analysis import views
from apps.analysis.services import model_catalog as mc
from apps.analysis.services.exceptions import ModelsUnavailableError
from apps.analysis.services.pipeline import AnalysisResult, CharacterGroup, EntityMention, RoleResult

URL = reverse("analysis:workspace")
TEXT = "I Kancil luas ka tukade. Ditu ia nepukin I Kakua."


def fake_result(config, display_text="<script>alert(1)</script> I Kancil luas."):
    start = display_text.index("I Kancil")
    return AnalysisResult(
        config=config.as_dict(),
        display_text=display_text,
        sentences=[display_text],
        characters=["I Kancil"],
        mentions=[EntityMention("I Kancil", "ANM", 0, start, start + len("I Kancil"), "Tokoh-1")],
        groups=[CharacterGroup("Tokoh-1", 1, ["I Kancil", "Kancil"], 1, 1)],
        roles=[RoleResult("Tokoh-1", "Protagonis", "protagonis", 0.42, None, 8, None, True)],
        timings={"preprocess": 0.1, "identify": 1.0, "alias": 0.1, "role": 0.5},
        model_version={"balinese_nlp": "2.4.2", "scikit_learn": "1.2.1", "ner_model": config.ner_model,
                       "alias": {"method": config.alias_method, "threshold": config.alias_threshold},
                       "classifier": {"id": config.classifier_id, "file": "svm_pretrained_model.pkl", "sha256": "abc"}},
    )


@pytest.fixture
def captured(monkeypatch):
    calls = []

    def fake_pipeline(text, config):
        calls.append((text, config))
        return fake_result(config)

    monkeypatch.setattr(views, "run_full_pipeline", fake_pipeline)
    return calls


@pytest.mark.django_db
def test_anonymous_is_redirected_to_login(client):
    response = client.get(URL)
    assert response.status_code == 302 and reverse("account_login") in response["Location"]


@pytest.mark.django_db
def test_unverified_user_is_blocked(client, make_user):
    client.force_login(make_user(email="belum@example.com", verified=False))
    response = client.get(URL)
    assert response.status_code != 200 or "analysis-result" not in response.content.decode()
    assert "data-analysis-form" not in response.content.decode()


@pytest.mark.django_db
def test_get_shows_form_with_catalog_choices(client, verified_user):
    client.force_login(verified_user)
    html = client.get(URL).content.decode()

    assert "data-analysis-form" in html and 'lang="ban"' in html
    assert f'value="{mc.DEFAULT_CLASSIFIER_ID}" selected' in html
    assert "KNN · TF4 · F1 CV 0,6666 (Tabel 4.57) · F1 uji 0,6451 (Tabel 4.60) · bawaan" in html
    assert "SVM · TF5 · F1 CV 0,6811 (Tabel 4.59) · F1 uji 0,6460 (Tabel 4.60) · terbaik menurut tesis<" in html
    assert 'value="m1-lexicon-tf1-tf3-knn" disabled' in html
    assert ">Pengguna Umum<" in html and "Sederhana" not in html
    assert f'href="{URL}" data-reset' in html and ">Reset<" in html
    assert "0,6811" in html and "Tabel 4.59" in html
    assert "Copyright 2026 | I Made Satria Bimantara, S.Kom., M.Kom." in html


@pytest.mark.django_db
def test_sample_link_prefills_text(client, verified_user):
    client.force_login(verified_user)
    html = client.get(URL, {"contoh": "i-kancil"}).content.decode()
    assert "I Kancil" in html and "I Kakua" in html
    assert client.get(URL, {"contoh": "../../settings"}).status_code == 200


@pytest.mark.django_db
def test_invalid_text_shows_field_error(client, verified_user, captured):
    client.force_login(verified_user)
    html = client.post(URL, {"text": "tanpa titik sama sekali", "task": "full"}).content.decode()
    assert 'aria-invalid="true"' in html and "titik" in html
    assert captured == []


@pytest.mark.django_db
def test_simple_mode_uses_defaults_and_escapes_text(client, verified_user, captured):
    client.force_login(verified_user)
    response = client.post(URL, {"text": TEXT, "task": "full", "mode": "simple",
                                 "classifier_id": "m1-wordvector-tf4-svm", "ner_model": "hmm"})
    html = response.content.decode()

    assert captured[0][1] == mc.PipelineConfig()  # research choices ignored in simple mode
    assert 'value="m1-wordvector-tf4-svm" selected' in html  # the posted choice is kept in the panel
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html
    assert 'class="entity entity--protagonis entity--static"' in html
    assert ">ANM<" in html  # entity label badge
    assert "Protagonis" in html and "di bawah 0,70" in html
    assert "Konteks sedikit" in html


@pytest.mark.django_db
def test_simple_post_keeps_research_defaults(client, verified_user, captured):
    client.force_login(verified_user)
    html = client.post(URL, {"text": TEXT, "task": "full", "mode": "simple"}).content.decode()
    assert f'value="{mc.DEFAULT_CLASSIFIER_ID}" selected' in html
    assert 'value="jaro-distance" selected' in html and 'value="0.85"' in html


@pytest.mark.django_db
def test_advanced_mode_uses_research_choices(client, verified_user, captured):
    client.force_login(verified_user)
    client.post(URL, {"text": TEXT, "task": "alias", "mode": "advanced", "ner_model": "crf2_baseline",
                      "alias_method": "jaccard", "alias_threshold": "0.9", "classifier_id": "m1-wordvector-tf4-svm"})
    assert captured[0][1] == mc.PipelineConfig("alias", "crf2_baseline", "jaccard", 0.9, "m1-wordvector-tf4-svm")


@pytest.mark.django_db
@pytest.mark.parametrize("classifier_id", ["m1-lexicon-tf1-knn", "../x.pkl", "/etc/passwd"])
def test_unknown_or_unavailable_classifier_is_rejected(client, verified_user, captured, classifier_id):
    client.force_login(verified_user)
    response = client.post(URL, {"text": TEXT, "task": "full", "mode": "advanced", "classifier_id": classifier_id})
    assert response.status_code == 200 and captured == []


@pytest.mark.django_db
def test_model_failure_keeps_text(client, verified_user, monkeypatch):
    def broken(text, config):
        raise ModelsUnavailableError(detail="missing")

    monkeypatch.setattr(views, "run_full_pipeline", broken)
    client.force_login(verified_user)
    html = client.post(URL, {"text": TEXT, "task": "full"}).content.decode()
    assert 'role="alert"' in html and "Ditu ia nepukin I Kakua" in html
    assert "missing" not in html  # technical detail is never shown
