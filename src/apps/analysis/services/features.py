"""Classifier bundle navigation and text feature extraction (TF4, TF5), ported from scripts/prasibali_models.py.

Keep this in step with the script: same entry lookup, same extractor selection, same block order (file-name order,
e.g. TF4 then TF5), same feature-count check. Lexicon features (TF1-TF3) are not ported because their pickles
cannot be opened in v1.0 (catalog entries are available=False).

Extractor shapes supported by run_extractor():
  1. scikit-learn style, e.g. TfidfVectorizer for TF4: extractor.transform(contexts)
  2. balinese-nlp style (WordEmbeddingFeatureExtraction etc.): extractor.fit(contexts).transform(); when a stored
     WordEmbeddingFeatureExtraction has no embedding model, the FastText model is filled in
  3. a gensim model stored in the pickle (has .wv and .vector_size): averaged like WordEmbeddingFeatureExtraction
  4. TF5 without a stored extractor (None/str): FastText from the embedding loader, then averaged
Note: balinese-nlp extractors keep state in fit(); callers must not share one instance between threads.
"""

from __future__ import annotations

import contextlib
import inspect
import time
from collections.abc import Callable

from .exceptions import EmbeddingError, RoleClassificationError


def _structure(obj, depth: int = 3) -> str:
    if not isinstance(obj, dict):
        return type(obj).__name__
    if depth == 0:
        return f"dict({len(obj)} keys)"
    return "{" + ", ".join(f"{k!r}: {_structure(v, depth - 1)}" for k, v in list(obj.items())[:12]) + "}"


def _find_entry(obj, classifier_name: str, depth: int = 5):
    """Walk nested dicts; prefer branches named after the algorithm or 'pretrained_model'."""
    if not isinstance(obj, dict) or depth == 0:
        return None
    if "estimator" in obj:
        return obj
    preferred = [k for k in obj if k in (classifier_name, "pretrained_model")]
    for key in preferred + [k for k in obj if k not in preferred]:
        found = _find_entry(obj[key], classifier_name, depth - 1)
        if found is not None:
            return found
    return None


def extract_model_entry(bundle, classifier_name: str, bundle_keys: tuple[str, ...] = ()) -> dict:
    """Return the dict holding 'estimator' (and 'feature_extractor', {} when not stored).

    `bundle_keys` from the catalog is tried first (M1: (algorithm, 'pretrained_model'); M2: ('m2',)); otherwise the
    tree is searched like scripts/prasibali_models.extract_model_entry.
    """
    entry = bundle
    for key in bundle_keys:
        entry = entry.get(key) if isinstance(entry, dict) else None
    if not (isinstance(entry, dict) and "estimator" in entry):
        entry = _find_entry(bundle, classifier_name)
    if entry is None:
        detail = f"Unrecognised pickle structure for {classifier_name!r}: {_structure(bundle)}"
        raise RoleClassificationError(detail=detail)
    if "feature_extractor" not in entry:
        entry = {**entry, "feature_extractor": {}}
    return entry


def select_extractors(entry: dict, codes: list[str] | tuple[str, ...]) -> list[tuple[str, object]]:
    """Extractor per feature code, in file-name order. TF5 may be missing: it is defined by the FastText model."""
    codes = list(codes)
    extractors = entry["feature_extractor"]
    joined = "_".join(codes)
    if not isinstance(extractors, dict):
        return [(joined, extractors)]
    if len(codes) > 1 and joined in extractors:
        return [(joined, extractors[joined])]
    selected = []
    for code in codes:
        if code in extractors:
            selected.append((code, extractors[code]))
        elif code == "TF5" and not (len(codes) == 1 and len(extractors) == 1):
            selected.append((code, None))
        elif len(codes) == 1 and len(extractors) == 1:
            key, value = next(iter(extractors.items()))
            selected.append((str(key), value))
        else:
            raise RoleClassificationError(detail=f"Feature extractor {code} missing; keys: {list(extractors)}")
    return selected


def is_word_embedding_model(obj) -> bool:
    return hasattr(obj, "wv") and hasattr(obj, "vector_size")


def average_word_vectors(model, contexts: list[str]):
    """TF5: mean word vector per context via balinese-nlp WordEmbeddingFeatureExtraction (as in training).

    The fallback copies that class line by line (words split on spaces, only words in model.wv, zeros when none).
    """
    import numpy as np

    try:
        from balinese_nlp.feature_extractor.narratives.characterclassification.WordEmbeddingFeatureExtraction import (
            WordEmbeddingFeatureExtraction,
        )
    except ImportError:
        WordEmbeddingFeatureExtraction = None
    if WordEmbeddingFeatureExtraction is not None:
        return WordEmbeddingFeatureExtraction(pretrained_word_embedding=model).fit(list(contexts)).transform()
    rows = []
    for sentence in contexts:
        vectors = [model.wv[word] for word in sentence.split() if word in model.wv]
        rows.append(sum(vectors) / len(vectors) if vectors else np.zeros(model.vector_size))
    return np.array(rows)


def _transform_takes_input(extractor) -> bool:
    """True for scikit-learn transform(X); False for balinese-nlp fit(X).transform()."""
    try:
        params = inspect.signature(extractor.transform).parameters.values()
    except (TypeError, ValueError):
        return True
    return any(p.default is inspect.Parameter.empty and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
               for p in params)


def run_extractor(code: str, extractor, contexts: list[str], embedding_loader: Callable[[], object] | None):
    """Run one extractor; returns (matrix, how)."""
    transform = getattr(extractor, "transform", None)
    if callable(transform) and _transform_takes_input(extractor):
        return extractor.transform(contexts), "transform(X)"
    if callable(transform) and callable(getattr(extractor, "fit", None)):
        embedding = getattr(extractor, "pretrained_word_embedding", None)
        if hasattr(extractor, "pretrained_word_embedding") and not is_word_embedding_model(embedding):
            if embedding_loader is None:
                raise EmbeddingError(detail=f"Extractor {code} needs a word embedding but no loader was given")
            extractor.pretrained_word_embedding = embedding_loader()
        return extractor.fit(list(contexts)).transform(), "fit(X).transform()"
    if is_word_embedding_model(extractor):
        return average_word_vectors(extractor, contexts), "mean word vector (model in pickle)"
    if code == "TF5" and (extractor is None or isinstance(extractor, str)):
        if embedding_loader is None:
            raise EmbeddingError(detail="Feature TF5 needs FastText but no embedding loader was given")
        return average_word_vectors(embedding_loader(), contexts), "mean word vector (FastText)"
    kind = f"{type(extractor).__module__}.{type(extractor).__name__}"
    raise RoleClassificationError(detail=f"Unrecognised extractor for {code}: {kind}")


def featurize(selected, contexts: list[str], embedding_loader=None, scaler=None):
    """Feature matrix with the blocks of each code side by side, plus known TF-IDF terms per context (or None).

    Returns (X, known_terms, timings) where timings maps feature code -> seconds.
    """
    import numpy as np

    blocks, known_terms, timings = [], None, {}
    for code, extractor in selected:
        started = time.perf_counter()
        matrix, _how = run_extractor(code, extractor, contexts, embedding_loader)
        matrix = matrix.toarray() if hasattr(matrix, "toarray") else np.asarray(matrix, dtype=float)
        if matrix.ndim != 2 or matrix.shape[0] != len(contexts):
            detail = f"Extractor {code} returned shape {matrix.shape}, expected ({len(contexts)}, n)"
            raise RoleClassificationError(detail=detail)
        timings[code] = round(time.perf_counter() - started, 3)
        if hasattr(extractor, "vocabulary_"):
            known_terms = [int(n) for n in (matrix != 0).sum(axis=1)]
        blocks.append(matrix)
    features = np.hstack(blocks) if len(blocks) > 1 else blocks[0]
    if scaler is not None:
        check_feature_count(scaler, features)
        features = scaler.transform(features)
    return features, known_terms, timings


def check_feature_count(estimator, features) -> None:
    expected = getattr(estimator, "n_features_in_", None)
    if expected is not None and features.shape[1] != expected:
        raise RoleClassificationError(
            detail=f"{features.shape[1]} features, model expects {expected}; feature order or combination differs"
        )


def score_and_probability(estimator, features) -> tuple[list, list]:
    """decision_function score (when available) and probability of the chosen class (when supported)."""
    import numpy as np

    n = features.shape[0]
    scores: list = [None] * n
    probabilities: list = [None] * n
    if callable(getattr(estimator, "decision_function", None)):
        raw = np.asarray(estimator.decision_function(features))
        scores = [round(float(v if raw.ndim == 1 else np.max(v)), 4) for v in raw]
    if callable(getattr(estimator, "predict_proba", None)):
        with contextlib.suppress(Exception):  # e.g. SVC without probability=True
            probabilities = [round(float(np.max(row)), 4) for row in estimator.predict_proba(features)]
    return scores, probabilities


def find_encoder(obj):
    """LabelEncoder inside the encoder pickle; known path ['train']['y_encoder']."""
    if hasattr(obj, "inverse_transform") and hasattr(obj, "classes_"):
        return obj
    if isinstance(obj, dict):
        for key in ("train", "y_encoder"):
            if key in obj and (found := find_encoder(obj[key])) is not None:
                return found
        for value in obj.values():
            if (found := find_encoder(value)) is not None:
                return found
    return None


def tf5_dimensions(estimator, selected) -> int | None:
    """Number of feature columns the estimator expects from TF5 (n_features_in_ minus the TF-IDF vocabulary)."""
    expected = getattr(estimator, "n_features_in_", None)
    if expected is None or not any(code == "TF5" for code, _ in selected):
        return None
    other = 0
    for code, extractor in selected:
        if code == "TF5":
            continue
        vocabulary = getattr(extractor, "vocabulary_", None)
        if vocabulary is None:
            return None  # cannot tell; check_feature_count still guards at prediction time
        other += len(vocabulary)
    return expected - other
