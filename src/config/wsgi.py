import logging
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

application = get_wsgi_application()


def _warm_models() -> None:
    """Load the default AI models before serving (with gunicorn --preload: once, shared by the workers).

    A failure is logged and never stops the server: the analysis view reports the unavailable stage instead.
    """
    from django.conf import settings

    if not settings.ANALYSIS_WARM_ON_START:
        return
    from apps.analysis.services import model_registry
    from apps.analysis.services.exceptions import AnalysisError

    try:
        model_registry.warm_up()
    except AnalysisError as exc:
        logging.getLogger("apps.analysis").error("Model warm-up failed: %s", exc.detail or exc)


_warm_models()
