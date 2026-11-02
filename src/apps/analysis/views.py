from pathlib import Path

from allauth.account.decorators import verified_email_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .forms import AnalysisForm
from .presenters import present
from .services.exceptions import AnalysisError, TextValidationError
from .services.pipeline import run_full_pipeline

SAMPLE_DIR = Path(__file__).resolve().parent / "data" / "sample_satua"
# Whitelisted sample stories for the "Try a sample satua" links: slug -> (title, file name).
SAMPLES = {
    "i-kancil": ("I Kancil Nulungin I Kakua", "i_kancil_nulungin_i_kakua.txt"),
    "ni-luh-sari": ("Ni Luh Sari teken Men Sugih", "ni_luh_sari_teken_men_sugih.txt"),
}


def load_sample(slug: str) -> str | None:
    if slug not in SAMPLES:
        return None
    return (SAMPLE_DIR / SAMPLES[slug][1]).read_text(encoding="utf-8")


@verified_email_required
@require_http_methods(["GET", "POST"])
def workspace(request):
    """Analysis workspace. Plain POST and full-page render for now; HTMX, history and quota follow in session 4."""
    initial = {}
    sample = load_sample(request.GET.get("contoh", ""))
    if sample:
        initial["text"] = sample
    form = AnalysisForm(request.POST or None, initial=initial)
    view, error = None, None
    if request.method == "POST" and form.is_valid():
        try:
            view = present(run_full_pipeline(form.cleaned_data["text"], form.config()))
        except TextValidationError as exc:
            form.add_error("text", exc.user_message)
        except AnalysisError as exc:
            error = exc.user_message
    return render(request, "analysis/workspace.html", {
        "form": form,
        "view": view,
        "error": error,
        "samples": [(slug, title) for slug, (title, _file) in SAMPLES.items()],
    })
