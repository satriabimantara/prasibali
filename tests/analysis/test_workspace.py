"""Analysis workspace view. The pipeline is replaced by a fake result, so no models are loaded (runs in CI)."""

import json

import pytest
from analysis_fakes import TEXT, fake_result
from django.urls import reverse

from apps.analysis import views
from apps.analysis.models import AnalysisRun
from apps.analysis.services import model_catalog as mc
from apps.analysis.services.exceptions import ModelsUnavailableError, TextValidationError

URL = reverse("analysis:workspace")
HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture
def captured(monkeypatch):
    calls = []

    def fake_pipeline(text, config):
        calls.append((text, config))
        return fake_result(config)

    monkeypatch.setattr(views, "run_full_pipeline", fake_pipeline)
    return calls


@pytest.fixture
def logged_in(client, verified_user, settings):
    settings.ANALYSIS_DAILY_QUOTA = 10  # independent of the developer's .env
    client.force_login(verified_user)
    return client


# --------------------------------------------------------------------------- access
@pytest.mark.django_db
def test_anonymous_is_redirected_to_login(client):
    response = client.get(URL)
    assert response.status_code == 302 and reverse("account_login") in response["Location"]


@pytest.mark.django_db
def test_htmx_request_after_session_end_redirects_whole_page(client):
    response = client.post(URL, {"text": TEXT}, **HTMX)
    assert response.status_code == 200
    assert response["HX-Redirect"].startswith(reverse("account_login"))


@pytest.mark.django_db
def test_unverified_user_is_blocked(client, make_user):
    client.force_login(make_user(email="belum@example.com", verified=False))
    response = client.get(URL)
    assert response.status_code != 200 or "analysis-result" not in response.content.decode()
    assert "data-analysis-form" not in response.content.decode()


# --------------------------------------------------------------------------- form and research panel
@pytest.mark.django_db
def test_get_shows_form_htmx_and_research_panel(logged_in):
    html = logged_in.get(URL).content.decode()

    assert "data-analysis-form" in html and 'lang="ban"' in html
    assert 'hx-post="/analisis/"' in html and 'hx-target="#workspace"' in html
    assert "htmx-2.0.4.min.js" in html and "alpinejs-3.14.8.min.js" in html and "research.js" in html
    assert f'name="classifier_id" value="{mc.DEFAULT_CLASSIFIER_ID}"' in html
    assert "classifierPicker('m2-wordvector-tf4-knn')" in html and "{ task: 'full' }" in html
    assert ">Pengguna Umum<" in html and "Sederhana" not in html
    assert f'href="{URL}" data-reset' in html and ">Reset<" in html
    assert "Sisa kuota hari ini: 10 dari 10 analisis" in html
    assert 'aria-current="page"' in html and "Riwayat analisis" in html
    assert "Copyright 2026 | I Made Satria Bimantara, S.Kom., M.Kom." in html


@pytest.mark.django_db
def test_research_catalog_json_drives_the_cascade(logged_in):
    html = logged_in.get(URL).content.decode()
    raw = html.split('<script id="classifier-catalog" type="application/json">')[1].split("</script>")[0]
    catalog = json.loads(raw)
    entries = {e["id"]: e for e in catalog["entries"]}

    assert set(entries) == set(mc.CLASSIFIERS) and catalog["defaultId"] == mc.DEFAULT_CLASSIFIER_ID
    default = entries[mc.DEFAULT_CLASSIFIER_ID]
    assert default["tags"] == ["bawaan", "rekomendasi"] and default["f1Cv"] == "0,6666"
    assert default["f1Test"] == "0,6451" and default["refTest"] == "Tabel 4.60"
    best = entries[mc.THESIS_BEST_CLASSIFIER_ID]
    assert best["tags"] == ["terbaik menurut tesis"] and best["f1Cv"] == "0,6811" and best["refCv"] == "Tabel 4.59"
    assert "bukan probabilitas" in best["score"]
    lexicon = entries["m1-lexicon-tf1-tf3-knn"]
    assert lexicon["available"] is False and "segera hadir" in lexicon["tags"]
    # A combination that the thesis did not test on test data has no test F1.
    assert entries["m1-wordvector-tf4-svm"]["f1Test"] == "–" and entries["m1-wordvector-tf4-svm"]["refTest"] == ""
    assert [v["id"] for v in catalog["variants"]] == ["m2", "m1"]
    assert "300 dimensi" in catalog["features"]["TF5"]
    assert "0,5395" in catalog["baseline"]


@pytest.mark.django_db
def test_sample_link_prefills_text(logged_in):
    html = logged_in.get(URL, {"contoh": "i-kancil"}).content.decode()
    assert "I Kancil" in html and "I Kakua" in html
    assert logged_in.get(URL, {"contoh": "../../settings"}).status_code == 200


@pytest.mark.django_db
def test_invalid_text_shows_field_error_and_uses_no_quota(logged_in, verified_user, captured):
    html = logged_in.post(URL, {"text": "tanpa titik sama sekali", "task": "full"}).content.decode()
    assert 'aria-invalid="true"' in html and "titik" in html
    assert captured == [] and AnalysisRun.objects.count() == 0


# --------------------------------------------------------------------------- running an analysis
@pytest.mark.django_db
def test_simple_mode_uses_defaults_escapes_text_and_records_run(logged_in, verified_user, captured):
    response = logged_in.post(URL, {"text": TEXT, "task": "full", "mode": "simple",
                                    "classifier_id": "m1-wordvector-tf4-svm", "ner_model": "hmm"})
    html = response.content.decode()

    assert captured[0][1] == mc.PipelineConfig()  # research choices ignored in simple mode
    assert 'name="classifier_id" value="m1-wordvector-tf4-svm"' in html  # the posted choice stays in the panel
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html
    assert 'class="entity entity--protagonis" data-char="Tokoh-1"' in html
    assert '<span class="entity-tag entity-tag--anm">ANM' in html
    assert '<span class="entity-tag entity-tag--pname">PNAME' in html
    assert "Protagonis" in html and "di bawah 0,70" in html
    assert "Konteks sedikit" in html

    run = AnalysisRun.objects.get()
    assert run.user == verified_user and run.status == AnalysisRun.Status.SUCCESS
    assert run.task_type == "full" and run.input_text == TEXT
    assert run.config == {**mc.PipelineConfig().as_dict(), "mode": "simple"}
    assert run.model_version["classifier"]["sha256"] == "abc" and run.duration_ms is not None
    assert run.output["roles"][0]["role"] == "Protagonis"
    assert reverse("analysis:history_detail", args=[run.pk]) in html


@pytest.mark.django_db
def test_htmx_post_returns_workspace_partial_only(logged_in, captured):
    response = logged_in.post(URL, {"text": TEXT, "task": "full"}, **HTMX)
    html = response.content.decode()

    assert response.status_code == 200 and "HX-Request" in response["Vary"]
    assert html.lstrip().startswith('<div id="workspace"')
    assert "<html" not in html and "site_footer" not in html
    assert 'id="analysis-result"' in html and 'id="analysis-loading"' in html


@pytest.mark.django_db
def test_selected_character_shows_sentence_context(logged_in, captured):
    html = logged_in.post(URL, {"text": TEXT, "task": "full"}).content.decode()

    assert 'id="context-panel"' in html
    block = html.split('data-context-for="Tokoh-1"')[1].split("</ol>")[0]
    assert "Disebut dalam 2 kalimat" in block
    assert '<mark class="context-mark">I Kancil</mark>' in block
    assert '<mark class="context-mark">Kancil</mark> nepukin I Kakua.' in block  # only this character is marked
    assert 'data-char="Tokoh-2" aria-pressed="false" aria-controls="context-panel"' in html  # group card button


@pytest.mark.django_db
def test_scores_are_explained_and_never_called_confidence(logged_in, captured):
    html = logged_in.post(URL, {"text": TEXT, "task": "full", "mode": "advanced",
                                "classifier_id": "m2-wordvector-tf5-svm"}).content.decode()
    assert "decision_function SVM" in html and "bukan probabilitas" in html
    assert "0,4200" in html and "-0,3000" in html
    assert "keyakinan" not in html.lower()


@pytest.mark.django_db
def test_advanced_mode_uses_research_choices(logged_in, captured):
    logged_in.post(URL, {"text": TEXT, "task": "alias", "mode": "advanced", "ner_model": "crf2_baseline",
                         "alias_method": "jaccard", "alias_threshold": "0.9", "classifier_id": "m1-wordvector-tf4-svm"})
    assert captured[0][1] == mc.PipelineConfig("alias", "crf2_baseline", "jaccard", 0.9, "m1-wordvector-tf4-svm")
    assert AnalysisRun.objects.get().config["mode"] == "advanced"


@pytest.mark.django_db
def test_models_panel_records_the_display_mode(logged_in, captured):
    html = logged_in.post(URL, {"text": TEXT, "task": "full", "mode": "advanced"}).content.decode()
    panel = html.split('id="models-title"')[1]
    assert "<dd>Lanjutan (Mode Peneliti)</dd>" in panel and "CRF-2" not in panel


@pytest.mark.django_db
@pytest.mark.parametrize("classifier_id", ["m1-lexicon-tf1-knn", "../x.pkl", "/etc/passwd", "M2-WORDVECTOR-TF5-SVM"])
def test_unknown_or_unavailable_classifier_is_rejected(logged_in, captured, classifier_id):
    response = logged_in.post(URL, {"text": TEXT, "task": "full", "mode": "advanced", "classifier_id": classifier_id})
    assert response.status_code == 200 and captured == []
    assert AnalysisRun.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("field,value", [("ner_model", "../../evil"), ("alias_method", "levenshtein"),
                                         ("alias_threshold", "2"), ("task", "coreference")])
def test_other_research_choices_are_whitelisted(logged_in, captured, field, value):
    data = {"text": TEXT, "task": "full", "mode": "advanced", field: value}
    assert logged_in.post(URL, data).status_code == 200 and captured == []


@pytest.mark.django_db
def test_model_failure_keeps_text_and_is_logged(logged_in, monkeypatch):
    def broken(text, config):
        raise ModelsUnavailableError(detail="missing pickle")

    monkeypatch.setattr(views, "run_full_pipeline", broken)
    html = logged_in.post(URL, {"text": TEXT, "task": "full"}).content.decode()
    assert 'role="alert"' in html and "Ditu ia nepukin I Kakua" in html
    assert "missing pickle" not in html  # technical detail is never shown
    run = AnalysisRun.objects.get()
    assert run.status == AnalysisRun.Status.FAILED and run.error_stage == "role"
    assert run.error_detail == "missing pickle" and run.error_message


@pytest.mark.django_db
def test_unexpected_exception_is_recorded_as_failed(logged_in, monkeypatch):
    def crash(text, config):
        raise RuntimeError("boom")

    monkeypatch.setattr(views, "run_full_pipeline", crash)
    html = logged_in.post(URL, {"text": TEXT, "task": "full"}).content.decode()
    assert 'role="alert"' in html and "boom" not in html
    assert AnalysisRun.objects.get().status == AnalysisRun.Status.FAILED


@pytest.mark.django_db
def test_text_rejected_by_the_pipeline_is_a_form_error(logged_in, monkeypatch):
    def reject(text, config):
        raise TextValidationError("no_sentences", "Teks tidak memiliki kalimat.")

    monkeypatch.setattr(views, "run_full_pipeline", reject)
    html = logged_in.post(URL, {"text": TEXT, "task": "full"}).content.decode()
    assert "Teks tidak memiliki kalimat." in html and 'aria-invalid="true"' in html
    assert AnalysisRun.objects.count() == 0


@pytest.mark.django_db
def test_identify_only_lists_characters_without_roles(logged_in, monkeypatch):
    def identify_only(text, config):
        result = fake_result(config)
        result.groups, result.roles = [], []
        for mention in result.mentions:
            mention.group_id = None
        return result

    monkeypatch.setattr(views, "run_full_pipeline", identify_only)
    html = logged_in.post(URL, {"text": TEXT, "task": "identify"}).content.decode()
    assert 'class="entity entity--none" data-char="n' in html
    assert "Tokoh yang ditemukan" in html and "di bawah 0,70" not in html
    assert 'data-context-for="n1"' in html


# --------------------------------------------------------------------------- task preselected from feature pages
@pytest.mark.django_db
@pytest.mark.parametrize("task", ["identify", "alias", "role"])
def test_task_query_preselects_task(logged_in, task):
    response = logged_in.get(URL, {"tugas": task})
    assert response.context["form"]["task"].value() == task


@pytest.mark.django_db
def test_unknown_task_query_is_ignored(logged_in):
    response = logged_in.get(URL, {"tugas": "../evil"})
    assert response.status_code == 200
    assert response.context["form"]["task"].value() == mc.DEFAULT_TASK
