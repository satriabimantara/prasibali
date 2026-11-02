"""Settings shared by every environment. Values come from the environment (or .env at the repo root)."""

from pathlib import Path

import environ
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # src/
REPO_ROOT = BASE_DIR.parent

env = environ.Env()
if (REPO_ROOT / ".env").is_file():
    # Real environment variables (e.g. set by docker compose) take precedence over .env.
    env.read_env(REPO_ROOT / ".env", overwrite=False)

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.accounts",
    "apps.analysis",
    "apps.pages",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {"default": env.db("DATABASE_URL")}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization: Indonesian is the default interface language, English the alternative.
LANGUAGE_CODE = "id"
LANGUAGES = [("id", _("Indonesian")), ("en", _("English"))]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Asia/Makassar"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = REPO_ROOT / "staticfiles"

# --- AI / NLP ------------------------------------------------------------------
# Folder holding the thesis pickles (character-classification/, label-encoder/, ...).
PRETRAINED_MODELS_DIR = env("PRETRAINED_MODELS_DIR", default="")
# FastText for feature TF5; empty means the defaults in scripts/prasibali_models.py.
TF5_HF_REPO_ID = env("TF5_HF_REPO_ID", default="")
TF5_FASTTEXT_FILENAME = env("TF5_FASTTEXT_FILENAME", default="")
# Maximum length of a submitted satua.
ANALYSIS_MAX_CHARS = 20_000
