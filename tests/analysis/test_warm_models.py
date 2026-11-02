"""warm_models command, with the registry mocked so CI loads no models."""

import pytest
from django.core.management import CommandError, call_command

from apps.analysis.services import model_registry
from apps.analysis.services.exceptions import ModelsUnavailableError


def test_warm_models_reports_timings(monkeypatch, capsys):
    calls = {}

    def fake_warm_up(include_embedding=True, log=None):
        calls["include_embedding"] = include_embedding
        log("NER satuaner: 0.1s")
        return {"NER satuaner": 0.1}

    monkeypatch.setattr(model_registry, "warm_up", fake_warm_up)
    call_command("warm_models", "--skip-embedding")

    out = capsys.readouterr().out
    assert calls == {"include_embedding": False}
    assert "NER satuaner" in out and "Models ready" in out


def test_warm_models_fails_with_clear_message(monkeypatch):
    def broken(include_embedding=True, log=None):
        raise ModelsUnavailableError(detail="PRETRAINED_MODELS_DIR is not set")

    monkeypatch.setattr(model_registry, "warm_up", broken)
    with pytest.raises(CommandError, match="PRETRAINED_MODELS_DIR"):
        call_command("warm_models", "--skip-embedding")


def test_missing_models_dir_raises_models_unavailable(settings):
    settings.PRETRAINED_MODELS_DIR = ""
    model_registry.get_label_encoder.cache_clear()
    with pytest.raises(ModelsUnavailableError):
        model_registry.get_label_encoder()
    model_registry.get_label_encoder.cache_clear()
