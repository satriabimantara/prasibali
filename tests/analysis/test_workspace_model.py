"""End to end through the real models: HTMX request -> pipeline -> AnalysisRun -> rendered result -> history."""

import pytest
from django.urls import reverse

from apps.analysis.models import AnalysisRun
from apps.analysis.services import model_catalog as mc
from apps.analysis.views import load_sample

pytestmark = [pytest.mark.model, pytest.mark.django_db]


@pytest.fixture
def logged_in(client, verified_user, settings):
    settings.ANALYSIS_DAILY_QUOTA = 10
    client.force_login(verified_user)
    return client


def test_default_pipeline_end_to_end(logged_in, verified_user):
    text = load_sample("i-kancil")
    response = logged_in.post(reverse("analysis:workspace"), {"text": text, "task": "full", "mode": "simple"},
                              HTTP_HX_REQUEST="true")
    html = response.content.decode()

    run = AnalysisRun.objects.get(user=verified_user)
    assert run.status == AnalysisRun.Status.SUCCESS, run.error_detail
    assert run.model_version["classifier"]["id"] == mc.DEFAULT_CLASSIFIER_ID
    assert len(run.model_version["classifier"]["sha256"]) == 12
    assert run.output["roles"] and run.duration_ms > 0

    assert 'class="entity entity--' in html and "entity-tag--" in html
    assert "data-context-for=" in html and '<mark class="context-mark">' in html
    assert "Estimasi probabilitas (predict_proba)" in html  # KNN default: probability with explanation
    assert "di bawah 0,70" in html

    detail = logged_in.get(reverse("analysis:history_detail", args=[run.pk])).content.decode()
    assert "KNN" in detail or "K-Nearest Neighbor" in detail
    assert run.model_version["classifier"]["sha256"] in detail


def test_svm_score_sign_matches_label(logged_in, verified_user):
    logged_in.post(reverse("analysis:workspace"), {
        "text": load_sample("ni-luh-sari"), "task": "full", "mode": "advanced",
        "classifier_id": "m1-wordvector-tf4-svm",
    })
    run = AnalysisRun.objects.get(user=verified_user)
    assert run.status == AnalysisRun.Status.SUCCESS, run.error_detail
    for role in run.output["roles"]:
        # Encoder classes ['Antagonis', 'Protagonis']: positive decision_function = Protagonis (shown in the UI).
        assert (role["decision_score"] > 0) == (role["role"] == "Protagonis")
