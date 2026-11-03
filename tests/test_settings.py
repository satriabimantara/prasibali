import importlib
import sys

from django.conf import settings


def test_custom_user_model():
    assert settings.AUTH_USER_MODEL == "accounts.User"


def test_languages_indonesian_default_and_english():
    assert settings.LANGUAGE_CODE == "id"
    assert [code for code, _ in settings.LANGUAGES] == ["id", "en"]


def test_input_limit():
    assert settings.ANALYSIS_MAX_CHARS == 20_000


def test_prod_settings_enable_security_headers(monkeypatch):
    monkeypatch.setenv("DJANGO_SECRET_KEY", "test-only-not-a-secret")
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "prasibali.tech")
    monkeypatch.setenv("CSRF_TRUSTED_ORIGINS", "https://prasibali.tech")
    monkeypatch.setenv("DATABASE_URL", "sqlite://:memory:")
    sys.modules.pop("config.settings.prod", None)
    prod = importlib.import_module("config.settings.prod")
    try:
        assert prod.DEBUG is False
        assert prod.ALLOWED_HOSTS == ["prasibali.tech", "127.0.0.1", "localhost"]
        assert prod.CSRF_TRUSTED_ORIGINS == ["https://prasibali.tech"]
        assert prod.SECURE_SSL_REDIRECT is True
        assert prod.SECURE_HSTS_SECONDS >= 31_536_000
        assert prod.SESSION_COOKIE_SECURE and prod.CSRF_COOKIE_SECURE
        assert prod.X_FRAME_OPTIONS == "DENY"
        assert prod.SECURE_CONTENT_TYPE_NOSNIFF is True
        assert r"^healthz$" in prod.SECURE_REDIRECT_EXEMPT
        # Session 7: CSP without inline scripts, Permissions-Policy, shared cache, JSON logs.
        csp = dict(part.split(" ", 1) for part in prod.CONTENT_SECURITY_POLICY.split("; "))
        assert csp["script-src"] == "'self' 'unsafe-eval'" and "'unsafe-inline'" not in prod.CONTENT_SECURITY_POLICY
        assert csp["frame-ancestors"] == "'none'" and csp["form-action"] == "'self'"
        assert "camera=()" in prod.PERMISSIONS_POLICY
        assert prod.MIDDLEWARE[1] == "apps.pages.middleware.SecurityHeadersMiddleware"
        assert prod.CACHES["default"]["BACKEND"].endswith("DatabaseCache")
        assert prod.LOGGING["formatters"]["json"]["()"] == "config.jsonlog.JsonFormatter"
    finally:
        sys.modules.pop("config.settings.prod", None)
