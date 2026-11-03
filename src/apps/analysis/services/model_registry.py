"""Loads and caches models: SatuaNER (and the other NER models), the label encoder, classifier bundles, FastText.

- Everything is lazy and cached per process with lru_cache. warm_up() (management command `warm_models`, and
  config/wsgi.py when ANALYSIS_WARM_ON_START is set) loads SatuaNER, the label encoder, the default classifier and
  FastText before the first request, so `gunicorn --preload` shares them between workers.
- Classifier bundles are cached by file (ANALYSIS_CLASSIFIER_CACHE_SIZE bundles at most) so the six algorithms in
  one M1 file share a single load and RAM stays bounded.
- Paths come only from catalog entries (whitelisted ids), never from user input: unpickling can execute code.
- A missing folder or unreadable pickle raises ModelsUnavailableError; the rest of the app keeps working.
"""

from __future__ import annotations

import functools
import hashlib
import logging
import pickle
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

from . import embeddings
from .exceptions import CharacterIdentificationError, ModelsUnavailableError, UnknownModelError
from .features import extract_model_entry, find_encoder, select_extractors, tf5_dimensions
from .model_catalog import (
    DEFAULT_CLASSIFIER_ID,
    DEFAULT_NER_MODEL,
    LABEL_ENCODER_PATH,
    NER_MODELS,
    ClassifierEntry,
    get_classifier_entry,
)

logger = logging.getLogger(__name__)

# balinese-nlp extractors keep state between fit() and transform(): one featurize/predict at a time per process.
PREDICT_LOCK = threading.Lock()


def models_dir() -> Path:
    value = settings.PRETRAINED_MODELS_DIR
    if not value:
        raise ModelsUnavailableError(detail="PRETRAINED_MODELS_DIR is not set")
    path = Path(value)
    if not path.is_dir():
        raise ModelsUnavailableError(detail=f"PRETRAINED_MODELS_DIR is not a folder: {path}")
    return path


def fingerprint(path: Path) -> str:
    """Short SHA-256, the same identity scripts/prasibali_models.fingerprint() prints."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()[:12]


def _unpickle(path: Path):
    if not path.is_file():
        raise ModelsUnavailableError(detail=f"Pickle not found: {path}")
    try:
        with path.open("rb") as handle:
            return pickle.load(handle)  # noqa: S301 - see module docstring
    except Exception as exc:
        raise ModelsUnavailableError(detail=f"Could not load {path.name}: {exc!r}") from exc


# --------------------------------------------------------------------------- NER (task i)
@functools.lru_cache(maxsize=len(NER_MODELS))
def get_ner_model(name: str = DEFAULT_NER_MODEL):
    if name not in NER_MODELS:
        raise UnknownModelError(f"Unknown NER model: {name!r}")
    try:
        from balinese_nlp.narratives.utils import load_pretrained_character_ner_model

        from . import postag_cache

        postag_cache.install()  # one shared, memoised HMM POS tagger instead of one per token
        model = load_pretrained_character_ner_model(name)
    except Exception as exc:
        raise CharacterIdentificationError(detail=f"Could not load NER model {name}: {exc!r}") from exc
    if isinstance(model, dict):  # older pickle format
        model = model.get("optimal_best_all_train_model", model)
    return model


# --------------------------------------------------------------------------- classifier (task iii)
@dataclass(frozen=True)
class LabelEncoderInfo:
    encoder: object
    sha256: str


@functools.lru_cache(maxsize=1)
def get_label_encoder() -> LabelEncoderInfo:
    path = models_dir() / LABEL_ENCODER_PATH
    encoder = find_encoder(_unpickle(path))
    if encoder is None:
        raise ModelsUnavailableError(detail=f"No LabelEncoder inside {path.name}")
    return LabelEncoderInfo(encoder, fingerprint(path))


@dataclass(frozen=True)
class Bundle:
    content: object
    sha256: str
    filename: str


@functools.lru_cache(maxsize=max(1, int(getattr(settings, "ANALYSIS_CLASSIFIER_CACHE_SIZE", 4))))
def _load_bundle(relative_path: str) -> Bundle:
    path = models_dir() / relative_path
    started = time.perf_counter()
    content = _unpickle(path)
    logger.info("Classifier bundle %s loaded in %.1fs", relative_path, time.perf_counter() - started)
    return Bundle(content, fingerprint(path), path.name)


@dataclass(frozen=True)
class LoadedClassifier:
    entry: ClassifierEntry
    estimator: object
    extractors: tuple  # ((code, extractor), ...) in file-name order
    scaler: object | None
    sha256: str
    filename: str
    tf5_dimensions: int | None


def get_classifier(catalog_id: str = DEFAULT_CLASSIFIER_ID, *, with_embedding: bool = True) -> LoadedClassifier:
    """Estimator and extractors for a catalog id. With `with_embedding`, FastText is loaded and its size checked."""
    entry = get_classifier_entry(catalog_id)
    bundle = _load_bundle(entry.relative_path)
    model_entry = extract_model_entry(bundle.content, entry.algorithm, entry.bundle_keys)
    selected = tuple(select_extractors(model_entry, entry.feature_codes))
    loaded = LoadedClassifier(
        entry=entry,
        estimator=model_entry["estimator"],
        extractors=selected,
        scaler=model_entry.get("feature_scaler"),
        sha256=bundle.sha256,
        filename=bundle.filename,
        tf5_dimensions=tf5_dimensions(model_entry["estimator"], selected),
    )
    if with_embedding and entry.uses_tf5:
        embeddings.check_dimension(embeddings.load_fasttext(), loaded.tf5_dimensions)
    return loaded


def clear_caches() -> None:
    """For tests and after replacing model files."""
    get_ner_model.cache_clear()
    get_label_encoder.cache_clear()
    _load_bundle.cache_clear()
    embeddings.clear_cache()


def warm_up(include_embedding: bool = True, log=None) -> dict[str, float]:
    """Load the default models now (seconds per step). Raises the first AnalysisError it meets."""
    log = log or logger.info
    timings: dict[str, float] = {}

    def step(name, func):
        started = time.perf_counter()
        func()
        timings[name] = round(time.perf_counter() - started, 2)
        log(f"{name}: {timings[name]:.1f}s")

    step(f"NER {DEFAULT_NER_MODEL}", lambda: get_ner_model(DEFAULT_NER_MODEL))
    step("label encoder", get_label_encoder)
    step(f"classifier {DEFAULT_CLASSIFIER_ID}", lambda: get_classifier(DEFAULT_CLASSIFIER_ID, with_embedding=False))
    if include_embedding and get_classifier_entry(DEFAULT_CLASSIFIER_ID).uses_tf5:
        step("FastText (TF5)", lambda: get_classifier(DEFAULT_CLASSIFIER_ID, with_embedding=True))
    # One short analysis loads what the first request would otherwise pay for (TextPreprocessor dictionaries,
    # alias clustering and grouping imports, the shared POS tagger) and fills the POS cache with common words.
    step("pipeline warm-up", lambda: _warm_pipeline(include_roles=include_embedding))
    return timings


WARM_UP_TEXT = Path(__file__).resolve().parent.parent / "data" / "sample_satua" / "i_kancil_nulungin_i_kakua.txt"


def _warm_pipeline(include_roles: bool) -> None:
    from .model_catalog import validate_config
    from .pipeline import run_full_pipeline

    text = WARM_UP_TEXT.read_text(encoding="utf-8") if WARM_UP_TEXT.is_file() else "I Kancil luas ka alase."
    run_full_pipeline(text, validate_config(task="full" if include_roles else "alias"))
