"""The cached POS tagger must give exactly the package's output (tags and NER labels); only faster.

Uses only data shipped inside balinese-nlp (HMM POS tagger, SatuaNER), so it runs in CI as well.
"""

from pathlib import Path

import pytest

from apps.analysis.services import model_registry, postag_cache
from apps.analysis.services.preprocessing import preprocess_story

SAMPLE = Path(__file__).resolve().parents[2] / "src" / "apps" / "analysis" / "data" / "sample_satua"


@pytest.fixture(scope="module")
def sentences():
    return preprocess_story((SAMPLE / "ni_luh_sari_teken_men_sugih.txt").read_text(encoding="utf-8")).sentences


def test_tags_equal_a_fresh_tagger_per_token(sentences):
    from balinese_nlp.postag.HMM import HiddenMarkovModelPOSTag

    tokens = list(dict.fromkeys(t for s in sentences for t in s.split(" ")))[:120]
    tokens += ["Ni Luh", "xyzzy"]  # multi-word and unknown input behave the same too
    for token in tokens:
        assert postag_cache.predict_token(token) == HiddenMarkovModelPOSTag().predict(token), token


def test_empty_token_fails_like_the_package():
    from balinese_nlp.postag.HMM import HiddenMarkovModelPOSTag

    with pytest.raises(IndexError):
        HiddenMarkovModelPOSTag().predict("")
    with pytest.raises(IndexError):
        postag_cache.predict_token("")


def test_ner_labels_equal_package_behaviour(sentences):
    model = model_registry.get_ner_model("satuaner")  # installs the cache
    sample = sentences[:6]
    try:
        postag_cache.uninstall()
        original = [list(model.predict_sentence(s)[0]) for s in sample]
    finally:
        postag_cache.install()
    cached = [list(model.predict_sentence(s)[0]) for s in sample]
    assert cached == original


def test_install_is_idempotent():
    import importlib

    postag_cache.install()
    postag_cache.install()
    module = importlib.import_module(postag_cache.BASE_MODEL_MODULE)
    assert module.HiddenMarkovModelPOSTag is postag_cache.CachedHMMPOSTag
