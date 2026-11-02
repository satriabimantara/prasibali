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
