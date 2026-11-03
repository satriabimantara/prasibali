"""Speed-up for character identification: one shared, memoised HMM POS tagger inside balinese-nlp's NER.

Why: BaseModel._prepare_input_sentence (balinese-nlp 2.4.2) calls `HiddenMarkovModelPOSTag().predict(token)` for
every token. Each construction builds a new TextPreprocessor and Stemmer (reloading the Balinese dictionary),
opens hmmmodel.txt again (never closed), and every predict() parses that file again. For a 370-token satua this
took about 2.7 s of the 2.8 s analysis, while the CRF itself takes milliseconds.

What: the POS tag of one token depends only on the token and the fixed HMM model, so the tagger is created once
and its result is cached per token. The package's own POSTagFeatureExtraction also reuses one instance for many
predict() calls. The package files are not changed: install() rebinds the name `HiddenMarkovModelPOSTag` in the
BaseModel module only. tests/analysis/test_postag_cache.py checks that tags and NER output are identical.
"""

from __future__ import annotations

import functools
import importlib
import threading

BASE_MODEL_MODULE = "balinese_nlp.narratives.characterner.BaseModel"
CACHE_SIZE = 100_000  # distinct tokens; a few MB at most

_lock = threading.Lock()  # the shared tagger keeps state between its internal steps


@functools.lru_cache(maxsize=1)
def _shared_tagger():
    from balinese_nlp.postag.HMM import HiddenMarkovModelPOSTag

    return HiddenMarkovModelPOSTag()


@functools.lru_cache(maxsize=CACHE_SIZE)
def predict_token(token: str) -> str:
    with _lock:
        return _shared_tagger().predict(token)


class CachedHMMPOSTag:
    """Drop-in for `HiddenMarkovModelPOSTag()` as BaseModel uses it: construct, then predict(token)."""

    def predict(self, sentence: str) -> str:
        return predict_token(sentence)


def install() -> None:
    """Make balinese-nlp's NER models use the cached tagger. Safe to call more than once."""
    module = importlib.import_module(BASE_MODEL_MODULE)
    if module.HiddenMarkovModelPOSTag is not CachedHMMPOSTag:
        module.HiddenMarkovModelPOSTag = CachedHMMPOSTag


def uninstall() -> None:
    """Restore the package's tagger (used by tests that compare with the original behaviour)."""
    from balinese_nlp.postag.HMM import HiddenMarkovModelPOSTag

    importlib.import_module(BASE_MODEL_MODULE).HiddenMarkovModelPOSTag = HiddenMarkovModelPOSTag


def cache_info():
    return predict_token.cache_info()
