from django.db import DatabaseError, connection
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.accounts.models import PRIVACY_POLICY_VERSION
from apps.analysis.services import model_catalog as mc

from . import about as about_content
from .features import AVAILABLE_FEATURES, COMING_SOON_FEATURES, FEATURES_BY_SLUG


@never_cache
@require_GET
def healthz(request):
    """Liveness/readiness probe for Docker and Caddy. Checks the database; never loads AI models."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "error", "database": "unavailable"}, status=503)
    return JsonResponse({"status": "ok", "database": "ok"})


def landing(request):
    """Home page (DESIGN.md "Beranda"): problem, solution, three steps and a call to action."""
    return render(request, "pages/landing.html", {
        "features": AVAILABLE_FEATURES,
        "features_soon": COMING_SOON_FEATURES,
    })


def privacy(request):
    """Privacy policy shown at signup; the version is stored with each user's consent."""
    return render(request, "pages/privacy.html", {"policy_version": PRIVACY_POLICY_VERSION})


def about(request):
    """About page: the research behind PrasiBali.ai, the team, publications and software."""
    return render(request, "pages/about.html", {
        "team": about_content.TEAM,
        "publications": about_content.PUBLICATIONS,
        "software": about_content.SOFTWARE,
        "features": AVAILABLE_FEATURES,
    })


def feature(request, slug):
    """One page per feature. Model facts come from the catalog, never from the template."""
    item = FEATURES_BY_SLUG.get(slug)
    if item is None:
        raise Http404
    context = {"feature": item, "features": AVAILABLE_FEATURES}
    if item.available:
        context.update({
            "ner_models": list(mc.NER_MODELS.values()),
            "default_ner": mc.NER_MODELS[mc.DEFAULT_NER_MODEL],
            "alias_methods": list(mc.ALIAS_METHODS.values()),
            "default_alias": mc.ALIAS_METHODS[mc.DEFAULT_ALIAS_METHOD],
            "alias_threshold": mc.DEFAULT_ALIAS_THRESHOLD,
            "default_classifier": mc.get_classifier_entry(mc.DEFAULT_CLASSIFIER_ID, require_available=False),
            "best_classifier": mc.get_classifier_entry(mc.THESIS_BEST_CLASSIFIER_ID, require_available=False),
            "algorithms": [name for name, _label in mc.ALGORITHMS.values()],
        })
    return render(request, "pages/feature.html", context)
