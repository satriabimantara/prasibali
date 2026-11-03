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
    "allauth",
    "allauth.account",
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
    # Activates the signed-in user's preferred language (after authentication, overrides LocaleMiddleware).
    "apps.accounts.middleware.UserLanguageMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
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
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# --- Accounts (django-allauth) ---------------------------------------------------
# Email-only accounts; the email must be verified before the first login.
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_FORMS = {"signup": "apps.accounts.forms.SignupForm"}
ACCOUNT_EMAIL_SUBJECT_PREFIX = ""  # the sender name "PrasiBali.ai" already identifies us
ACCOUNT_ADAPTER = "apps.accounts.adapters.AccountAdapter"
# ACCOUNT_RATE_LIMITS keeps allauth's defaults (failed logins, password reset, confirmation emails).
# They use the default cache; with several Gunicorn workers a shared cache is needed (session 7).
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "analysis:workspace"
ACCOUNT_LOGOUT_REDIRECT_URL = "pages:landing"

# --- Email ---------------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="PrasiBali.ai <no-reply@prasibali.ai>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

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
# FastText for feature TF5: <PRETRAINED_MODELS_DIR>/balinese-word-embedding/<file> when present, otherwise
# Hugging Face. Empty means the defaults in apps/analysis/services/embeddings.py (300_fasttext_model.bin).
TF5_HF_REPO_ID = env("TF5_HF_REPO_ID", default="")
TF5_FASTTEXT_FILENAME = env("TF5_FASTTEXT_FILENAME", default="")
# Writable folder for balinese-nlp's RuleBasedSentenceGrouping ("saved_file"); empty = <system temp>/prasibali.
BALINESE_NLP_WORK_DIR = env("BALINESE_NLP_WORK_DIR", default="")
# Load the default models when the WSGI app starts (use with gunicorn --preload in production).
ANALYSIS_WARM_ON_START = env.bool("ANALYSIS_WARM_ON_START", default=False)
# At most this many classifier pickles stay in memory (an M1 file holds six algorithms).
ANALYSIS_CLASSIFIER_CACHE_SIZE = env.int("ANALYSIS_CLASSIFIER_CACHE_SIZE", default=4)
# Character groups with fewer context words get a "little context, less reliable" warning.
ANALYSIS_LOW_CONTEXT_WORDS = env.int("ANALYSIS_LOW_CONTEXT_WORDS", default=20)
# Maximum length of a submitted satua.
ANALYSIS_MAX_CHARS = 20_000
# Analyses per user per day (local day in TIME_ZONE); failed runs do not count. 0 = unlimited.
ANALYSIS_DAILY_QUOTA = env.int("ANALYSIS_DAILY_QUOTA", default=10)
