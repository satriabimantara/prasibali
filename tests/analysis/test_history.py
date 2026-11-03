"""History pages (list, detail with configuration, delete one, delete all), quota and the admin log. No models."""

from datetime import timedelta

import pytest
from analysis_fakes import TEXT, fake_result
from django.urls import reverse
from django.utils import timezone

from apps.analysis import views
from apps.analysis.models import AnalysisRun, DailyUsage
from apps.analysis.runs import QuotaStatus, local_today, quota_status
from apps.analysis.services import model_catalog as mc
from apps.analysis.services.exceptions import ModelsUnavailableError
from apps.analysis.services.pipeline import AnalysisResult

WORKSPACE = reverse("analysis:workspace")
HISTORY = reverse("analysis:history")


@pytest.fixture
def logged_in(client, verified_user, settings):
    settings.ANALYSIS_DAILY_QUOTA = 10
    client.force_login(verified_user)
    return client


@pytest.fixture
def fake_pipeline(monkeypatch):
    monkeypatch.setattr(views, "run_full_pipeline", lambda text, config: fake_result(config))


def make_run(user, **fields):
    config = mc.validate_config(classifier_id=mc.THESIS_BEST_CLASSIFIER_ID)
    result = fake_result(config)
    defaults = {
        "task_type": "full",
        "input_text": "I Siput lawan I Kancil\nI Kancil luas ka tukade.",
        "config": {**config.as_dict(), "mode": "advanced"},
        "output": result.as_dict(),
        "model_version": {**result.model_version,
                          "classifier": {"id": config.classifier_id, "file": "svm_pretrained_model.pkl",
                                         "sha256": "0123456789ab"}},
        "status": AnalysisRun.Status.SUCCESS,
        "duration_ms": 1234,
    }
    defaults.update(fields)
    return AnalysisRun.objects.create(user=user, **defaults)


# --------------------------------------------------------------------------- access and ownership
@pytest.mark.django_db
@pytest.mark.parametrize("name,args", [("analysis:history", []), ("analysis:history_delete_all", []),
                                       ("analysis:history_detail", ["00000000-0000-0000-0000-000000000000"]),
                                       ("analysis:history_delete", ["00000000-0000-0000-0000-000000000000"])])
def test_history_requires_login(client, name, args):
    response = client.get(reverse(name, args=args))
    assert response.status_code == 302 and reverse("account_login") in response["Location"]


@pytest.mark.django_db
def test_unverified_user_cannot_see_history(client, make_user):
    user = make_user(email="belum@example.com", verified=False)
    make_run(user)
    client.force_login(user)
    assert "I Siput lawan I Kancil" not in client.get(HISTORY).content.decode()


@pytest.mark.django_db
def test_other_users_runs_are_invisible(logged_in, make_user):
    other = make_run(make_user(email="lain@example.com"))
    assert "I Siput" not in logged_in.get(HISTORY).content.decode()
    assert logged_in.get(reverse("analysis:history_detail", args=[other.pk])).status_code == 404
    assert logged_in.post(reverse("analysis:history_delete", args=[other.pk])).status_code == 404
    logged_in.post(reverse("analysis:history_delete_all"))
    assert AnalysisRun.objects.filter(pk=other.pk).exists()


# --------------------------------------------------------------------------- list and detail
@pytest.mark.django_db
def test_list_shows_runs_newest_first(logged_in, verified_user):
    old = make_run(verified_user, input_text="Satua lawas.")
    AnalysisRun.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=1))
    make_run(verified_user, status=AnalysisRun.Status.FAILED, output=None, error_message="Gagal.")
    html = logged_in.get(HISTORY).content.decode()

    assert html.index("I Siput lawan I Kancil") < html.index("Satua lawas.")
    assert "status--failed" in html and "status--success" in html and "Lanjutan" in html
    assert "1,2 s" in html and "Hapus semua riwayat" in html
    assert "Hari ini Anda sudah memakai 0 dari 10 analisis" in html


@pytest.mark.django_db
def test_empty_history(logged_in):
    html = logged_in.get(HISTORY).content.decode()
    assert "Riwayat Anda masih kosong" in html and "Hapus semua riwayat" not in html


@pytest.mark.django_db
def test_detail_shows_model_configuration_and_result(logged_in, verified_user):
    run = make_run(verified_user)
    html = logged_in.get(reverse("analysis:history_detail", args=[run.pk])).content.decode()

    assert "Konfigurasi model" in html and "<dd>Lanjutan (Mode Peneliti)</dd>" in html
    assert "SatuaNER (CRF + BPSO)" in html and "Jaro distance" in html
    assert "M2 · Word vector · TF5 · Support Vector Machine" in html and "terbaik menurut tesis" in html
    assert "F1 makro CV 0,6811 (Tabel 4.59)" in html and "F1 makro uji 0,6460 (Tabel 4.60)" in html
    assert "svm_pretrained_model.pkl · sha256 0123456789ab" in html
    assert "balinese-nlp 2.4.2" in html
    # The stored result is shown again: highlights, groups, roles, disclaimer.
    assert 'class="entity entity--protagonis" data-char="Tokoh-1"' in html and "di bawah 0,70" in html
    assert 'id="models-title"' not in html  # configuration already shown above


@pytest.mark.django_db
def test_detail_of_failed_run_shows_message_and_text(logged_in, verified_user):
    run = make_run(verified_user, status=AnalysisRun.Status.FAILED, output=None, model_version={},
                   error_message="Model klasifikasi peran sedang tidak tersedia.", error_detail="secret path")
    html = logged_in.get(reverse("analysis:history_detail", args=[run.pk])).content.decode()
    assert "Model klasifikasi peran sedang tidak tersedia." in html and "I Kancil luas ka tukade." in html
    assert "secret path" not in html


@pytest.mark.django_db
def test_result_roundtrip_through_json():
    config = mc.validate_config()
    result = fake_result(config)
    restored = AnalysisResult.from_dict(result.as_dict())
    assert restored == result


# --------------------------------------------------------------------------- delete
@pytest.mark.django_db
def test_delete_one_asks_first_then_deletes(logged_in, verified_user):
    run, keep = make_run(verified_user), make_run(verified_user)
    url = reverse("analysis:history_delete", args=[run.pk])

    html = logged_in.get(url).content.decode()
    assert "Hapus analisis ini?" in html and AnalysisRun.objects.filter(pk=run.pk).exists()

    response = logged_in.post(url)
    assert response.status_code == 302 and response["Location"] == HISTORY
    assert not AnalysisRun.objects.filter(pk=run.pk).exists() and AnalysisRun.objects.filter(pk=keep.pk).exists()


@pytest.mark.django_db
def test_delete_all(logged_in, verified_user):
    make_run(verified_user), make_run(verified_user)
    url = reverse("analysis:history_delete_all")
    assert "2 analisis akan dihapus permanen" in logged_in.get(url).content.decode()
    logged_in.post(url)
    assert not AnalysisRun.objects.filter(user=verified_user).exists()


# --------------------------------------------------------------------------- quota
@pytest.mark.django_db
def test_quota_blocks_after_limit_and_counts_only_successful_runs(logged_in, verified_user, settings, monkeypatch):
    settings.ANALYSIS_DAILY_QUOTA = 2
    calls = {"n": 0}

    def flaky(text, config):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ModelsUnavailableError(detail="missing")
        return fake_result(config)

    monkeypatch.setattr(views, "run_full_pipeline", flaky)
    data = {"text": TEXT, "task": "full"}
    logged_in.post(WORKSPACE, data)  # failed: refunded
    assert quota_status(verified_user) == QuotaStatus(limit=2, used=0)
    logged_in.post(WORKSPACE, data)
    logged_in.post(WORKSPACE, data)
    assert quota_status(verified_user).exhausted

    html = logged_in.post(WORKSPACE, data).content.decode()
    assert calls["n"] == 3  # the fourth request never reached the pipeline
    assert "Kuota hari ini (2 analisis) sudah habis" in html and "disabled" in html
    assert AnalysisRun.objects.filter(user=verified_user).count() == 3


@pytest.mark.django_db
def test_deleting_history_does_not_restore_quota(logged_in, verified_user, settings, fake_pipeline):
    settings.ANALYSIS_DAILY_QUOTA = 1
    logged_in.post(WORKSPACE, {"text": TEXT, "task": "full"})
    logged_in.post(reverse("analysis:history_delete_all"))
    assert quota_status(verified_user).exhausted
    html = logged_in.post(WORKSPACE, {"text": TEXT, "task": "full"}).content.decode()
    assert "sudah habis" in html and not AnalysisRun.objects.exists()


@pytest.mark.django_db
def test_quota_is_per_user_and_per_local_day(verified_user, make_user, settings):
    settings.ANALYSIS_DAILY_QUOTA = 3
    DailyUsage.objects.create(user=verified_user, day=local_today(), used=3)
    DailyUsage.objects.create(user=verified_user, day=local_today() - timedelta(days=1), used=3)
    assert quota_status(verified_user).exhausted
    assert quota_status(make_user(email="lain@example.com")).remaining == 3
    tomorrow = timezone.now() + timedelta(days=1)
    assert quota_status(verified_user, now=tomorrow).remaining == 3


@pytest.mark.django_db
def test_zero_quota_means_unlimited(verified_user, settings):
    settings.ANALYSIS_DAILY_QUOTA = 0
    DailyUsage.objects.create(user=verified_user, day=local_today(), used=500)
    status = quota_status(verified_user)
    assert status.unlimited and not status.exhausted and status.remaining is None


@pytest.mark.django_db
def test_research_mode_shares_the_same_quota(logged_in, verified_user, settings, fake_pipeline):
    settings.ANALYSIS_DAILY_QUOTA = 1
    logged_in.post(WORKSPACE, {"text": TEXT, "task": "full", "mode": "advanced",
                               "classifier_id": "m2-wordvector-tf5-svm"})
    html = logged_in.post(WORKSPACE, {"text": TEXT, "task": "full", "mode": "simple"}).content.decode()
    assert "sudah habis" in html


# --------------------------------------------------------------------------- admin log
@pytest.mark.django_db
def test_admin_lists_runs_read_only(client, verified_user, django_user_model):
    run = make_run(verified_user, status=AnalysisRun.Status.FAILED, error_stage="role", error_detail="trace")
    admin = django_user_model.objects.create_superuser(email="admin@example.com", password="x")
    client.force_login(admin)

    changelist = client.get(reverse("admin:analysis_analysisrun_changelist")).content.decode()
    assert "ketut@example.com" in changelist and "m2-wordvector-tf5-svm" in changelist
    detail = client.get(reverse("admin:analysis_analysisrun_change", args=[run.pk])).content.decode()
    assert "trace" in detail and "0123456789ab" in detail
    assert client.get(reverse("admin:analysis_analysisrun_add")).status_code == 403
    assert client.get(reverse("admin:analysis_dailyusage_changelist")).status_code == 200
