from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.accounts.models import PRIVACY_POLICY_VERSION


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


def privacy(request):
    """Privacy policy shown at signup; the version is stored with each user's consent."""
    return render(request, "pages/privacy.html", {"policy_version": PRIVACY_POLICY_VERSION})
