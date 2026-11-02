from pathlib import Path

import pytest


def _models_dir_missing_reason() -> str | None:
    from django.conf import settings

    models_dir = settings.PRETRAINED_MODELS_DIR
    if not models_dir:
        return "PRETRAINED_MODELS_DIR is not set"
    if not Path(models_dir).is_dir():
        return f"PRETRAINED_MODELS_DIR is not a folder: {models_dir}"
    return None


def pytest_collection_modifyitems(config, items):
    """Skip tests marked `model` when the pretrained pickles are not available (e.g. GitHub Actions)."""
    reason = _models_dir_missing_reason()
    if reason is None:
        return
    skip = pytest.mark.skip(reason=reason)
    for item in items:
        if "model" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def models_dir() -> Path:
    from django.conf import settings

    return Path(settings.PRETRAINED_MODELS_DIR)


# --- Accounts ------------------------------------------------------------------
TEST_PASSWORD = "Satua-Bali-2026!"  # throwaway test value, not a secret


@pytest.fixture(autouse=True)
def _clear_cache():
    """allauth rate limits live in the cache; start every test with a clean slate."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def password() -> str:
    return TEST_PASSWORD


@pytest.fixture
def make_user(db):
    """Create a user; `verified=True` also adds a verified primary EmailAddress (as after confirmation)."""
    from allauth.account.models import EmailAddress
    from django.contrib.auth import get_user_model

    def factory(email="ketut@example.com", verified=True, **fields):
        fields.setdefault("full_name", "Ketut Satua")
        user = get_user_model().objects.create_user(email=email, password=TEST_PASSWORD, **fields)
        EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=verified)
        return user

    return factory


@pytest.fixture
def verified_user(make_user):
    return make_user()
