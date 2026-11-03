from functools import wraps
from pathlib import Path
from urllib.parse import urlencode

from allauth.account.decorators import verified_email_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render, resolve_url
from django.utils.cache import patch_vary_headers
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from .forms import AnalysisForm, research_catalog
from .models import AnalysisRun
from .presenters import present, present_config
from .runs import QuotaExceeded, execute_run, quota_message, quota_status, start_run
from .services import model_catalog as mc
from .services.exceptions import TextValidationError
from .services.pipeline import AnalysisResult, run_full_pipeline

SAMPLE_DIR = Path(__file__).resolve().parent / "data" / "sample_satua"
# Whitelisted sample stories for the "Try a sample satua" buttons: slug -> (title, file name).
SAMPLES = {
    "i-kancil": ("I Kancil Nulungin I Kakua", "i_kancil_nulungin_i_kakua.txt"),
    "ni-luh-sari": ("Ni Luh Sari teken Men Sugih", "ni_luh_sari_teken_men_sugih.txt"),
}
HISTORY_PAGE_SIZE = 20


def load_sample(slug: str) -> str | None:
    if slug not in SAMPLES:
        return None
    return (SAMPLE_DIR / SAMPLES[slug][1]).read_text(encoding="utf-8")


def is_htmx(request) -> bool:
    return request.headers.get("HX-Request") == "true"


def verified_login_required(view):
    """Login + verified email (allauth). An HTMX request whose session ended is sent to the login page as a whole
    page (HX-Redirect) instead of swapping the login form into the workspace."""
    protected = verified_email_required(view)

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if is_htmx(request) and not request.user.is_authenticated:
            response = HttpResponse()
            query = urlencode({"next": request.get_full_path()})
            response["HX-Redirect"] = f"{resolve_url('account_login')}?{query}"
            return response
        return protected(request, *args, **kwargs)

    return wrapper


def own_runs(request):
    return AnalysisRun.objects.filter(user=request.user)


# --------------------------------------------------------------------------- workspace
@verified_login_required
@require_http_methods(["GET", "POST"])
def workspace(request):
    initial = {}
    sample = load_sample(request.GET.get("contoh", ""))
    if sample:
        initial["text"] = sample
    task = request.GET.get("tugas", "")
    if task in mc.TASKS:  # whitelist: links from the feature pages preselect a task
        initial["task"] = task
    form = AnalysisForm(request.POST or None, initial=initial)
    view, error, run = None, None, None
    if request.method == "POST" and form.is_valid():
        config = form.config()
        try:
            run = start_run(request.user, form.cleaned_data["text"], config, form.cleaned_data.get("mode"))
            # Looked up here (not imported into runs.py) so tests can replace the pipeline on this module.
            result = execute_run(run, config, run_full_pipeline)
        except QuotaExceeded as exc:
            error = quota_message(exc.quota)
            run = None
        except TextValidationError as exc:
            form.add_error("text", exc.user_message)
            run = None
        else:
            if result is None:
                error = run.error_message
            else:
                view = present(result, duration_ms=run.duration_ms)
                # The run's config also records the display mode.
                view["config_view"] = present_config(run.config, run.model_version, result.timings, run.duration_ms)
    context = {
        "form": form,
        "view": view,
        "error": error,
        "run": run,
        "quota": quota_status(request.user),
        "catalog": research_catalog(),
        "samples": [(slug, title) for slug, (title, _file) in SAMPLES.items()],
        "nav": "workspace",
    }
    template = "analysis/partials/workspace_body.html" if is_htmx(request) else "analysis/workspace.html"
    response = render(request, template, context)
    patch_vary_headers(response, ("HX-Request",))
    return response


# --------------------------------------------------------------------------- history
@verified_login_required
@require_http_methods(["GET"])
def history_list(request):
    page = Paginator(own_runs(request), HISTORY_PAGE_SIZE).get_page(request.GET.get("halaman"))
    return render(request, "analysis/history_list.html", {
        "page": page,
        "quota": quota_status(request.user),
        "nav": "history",
    })


@verified_login_required
@require_http_methods(["GET"])
def history_detail(request, run_id):
    run = get_object_or_404(own_runs(request), pk=run_id)
    view, timings = None, {}
    if run.status == AnalysisRun.Status.SUCCESS and run.output:
        result = AnalysisResult.from_dict(run.output)
        view, timings = present(result, duration_ms=run.duration_ms), result.timings
    return render(request, "analysis/history_detail.html", {
        "run": run,
        "view": view,
        # The run's own config (with the display mode) and model_version are the record of what was used.
        "config_view": present_config(run.config, run.model_version, timings, run.duration_ms),
        "nav": "history",
    })


@verified_login_required
@require_http_methods(["GET", "POST"])
def history_delete(request, run_id):
    run = get_object_or_404(own_runs(request), pk=run_id)
    if request.method == "POST":
        run.delete()
        messages.success(request, _("The analysis has been deleted from your history."))
        return redirect("analysis:history")
    return render(request, "analysis/confirm_delete.html", {"run": run, "nav": "history"})


@verified_login_required
@require_http_methods(["GET", "POST"])
def history_delete_all(request):
    runs = own_runs(request)
    if request.method == "POST":
        deleted, _detail = runs.delete()
        messages.success(request, _("Your analysis history has been deleted (%(n)s items).") % {"n": deleted})
        return redirect("analysis:history")
    return render(request, "analysis/confirm_delete.html", {"run": None, "count": runs.count(), "nav": "history"})
