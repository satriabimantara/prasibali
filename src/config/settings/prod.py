"""Production settings: Gunicorn behind Caddy, which terminates HTTPS (docker-compose.prod.yml)."""

from django.core.exceptions import ImproperlyConfigured

from config.jsonlog import logging_config

from .base import *  # noqa: F403
from .base import EMAIL_USE_SSL, EMAIL_USE_TLS, MIDDLEWARE, env

DEBUG = False
# 127.0.0.1/localhost: the container healthcheck calls /healthz directly; Caddy forwards the public host.
ALLOWED_HOSTS = [*env.list("DJANGO_ALLOWED_HOSTS"), "127.0.0.1", "localhost"]
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")

# Hostinger SMTP: port 587 + STARTTLS (EMAIL_USE_TLS) or port 465 + SSL (EMAIL_USE_SSL), never both.
if EMAIL_USE_TLS and EMAIL_USE_SSL:
    raise ImproperlyConfigured("Set only one of EMAIL_USE_TLS (port 587) and EMAIL_USE_SSL (port 465).")

# Caddy forwards the original scheme.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SECURE_REDIRECT_EXEMPT = [r"^healthz$"]  # the container healthcheck talks plain HTTP
# Links in verification and password-reset emails.
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"

SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

# Content-Security-Policy (apps.pages.middleware.SecurityHeadersMiddleware). No inline scripts anywhere; the theme
# script is static/js/theme-init.js. 'unsafe-eval' is required by the standard Alpine.js build (Mode Peneliti panel),
# a developer decision in session 7. Fonts come from Google Fonts (DESIGN.md).
CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-eval'",
    "style-src 'self' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data:",
    "connect-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
])
PERMISSIONS_POLICY = ", ".join(
    f"{feature}=()" for feature in (
        "camera", "microphone", "geolocation", "payment", "usb", "accelerometer", "gyroscope", "magnetometer",
    )
)
MIDDLEWARE = [MIDDLEWARE[0], "apps.pages.middleware.SecurityHeadersMiddleware", *MIDDLEWARE[1:]]

# One cache shared by every Gunicorn worker (allauth login/reset rate limits) without Redis.
# The table is created by `manage.py createcachetable` in docker/entrypoint.sh.
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.db.DatabaseCache", "LOCATION": "django_cache"},
}

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

LOGGING = logging_config(env("DJANGO_LOG_LEVEL", default="INFO"))
