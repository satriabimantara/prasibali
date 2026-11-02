"""Balinese FastText word embedding for feature TF5 (mean word vector, 300 dimensions in the thesis).

Load order (developer decision, 3 Nov 2026):
  1. <PRETRAINED_MODELS_DIR>/balinese-word-embedding/<TF5_FASTTEXT_FILENAME> when that file exists (gensim);
  2. otherwise Hugging Face through balinese-nlp:
       BaliFastText(huggingface_repo_ID=TF5_HF_REPO_ID, pretrained_model_bin_filename=TF5_FASTTEXT_FILENAME)
     which downloads FastText/<file> and its .wv.vectors_ngrams.npy with hf_hub_download. huggingface_hub reads
     HF_HOME (cache folder, a persistent volume in Docker), HF_TOKEN (private repo) and HF_HUB_OFFLINE=1 (use the
     filled cache only) from the environment; BaliFastText has no revision parameter.
The file must be the one used to train the TF5 pickles: its vector_size must equal the TF5 part of the
classifier's n_features_in_ (check_dimension). The model is loaded once per process and never per request.
"""

from __future__ import annotations

import contextlib
import functools
import io
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from django.conf import settings

from .exceptions import EmbeddingError

logger = logging.getLogger(__name__)

DEFAULT_TF5_REPO_ID = "satriabimantara/balinese_pretrained_wordembedding"
# n_features_in_ of every TF5 estimator is 300 (--inspect, 2 Nov 2026), matching Tabel 3.10.
DEFAULT_TF5_FILENAME = "300_fasttext_model.bin"
LOCAL_EMBEDDING_DIR = "balinese-word-embedding"  # inside PRETRAINED_MODELS_DIR


@dataclass(frozen=True)
class EmbeddingSource:
    kind: str  # "local" | "huggingface"
    repo_id: str
    filename: str
    path: str | None  # local file path when kind == "local"

    def as_dict(self) -> dict:
        return asdict(self)


def embedding_source() -> EmbeddingSource:
    repo_id = settings.TF5_HF_REPO_ID or DEFAULT_TF5_REPO_ID
    filename = settings.TF5_FASTTEXT_FILENAME or DEFAULT_TF5_FILENAME
    name = Path(filename).name  # a bare file name; never a path from user input
    if settings.PRETRAINED_MODELS_DIR:
        local = Path(settings.PRETRAINED_MODELS_DIR) / LOCAL_EMBEDDING_DIR / name
        if local.is_file():
            return EmbeddingSource("local", repo_id, name, str(local))
    return EmbeddingSource("huggingface", repo_id, name, None)


@functools.lru_cache(maxsize=1)
def _load(source: EmbeddingSource):
    started = time.perf_counter()
    try:
        if source.kind == "local":
            from gensim.models import FastText

            model = FastText.load(source.path)  # own file; gensim uses pickle internally
        else:
            from balinese_nlp.embeddings.gensims import BaliFastText

            with contextlib.redirect_stdout(io.StringIO()):
                model = BaliFastText(
                    huggingface_repo_ID=source.repo_id, pretrained_model_bin_filename=source.filename,
                ).load_pretrained_model()
    except Exception as exc:
        detail = f"Could not load FastText {source.kind} {source.repo_id}/{source.filename}: {exc!r}"
        raise EmbeddingError(detail=detail) from exc
    logger.info("FastText %s loaded from %s in %.1fs (vector_size %s)", source.filename, source.kind,
                time.perf_counter() - started, getattr(model, "vector_size", "?"))
    return model


def load_fasttext():
    return _load(embedding_source())


def is_loaded() -> bool:
    return _load.cache_info().currsize > 0


def clear_cache() -> None:
    _load.cache_clear()


def check_dimension(model, expected: int | None) -> None:
    """Raise EmbeddingError when the embedding does not have the dimensions the classifier was trained with."""
    if expected is None:
        return
    size = getattr(model, "vector_size", None)
    if size != expected:
        raise EmbeddingError(
            detail=(f"FastText vector_size {size} differs from the {expected} TF5 features the classifier expects. "
                    "Set TF5_FASTTEXT_FILENAME to the file used to train the TF5 pickles.")
        )


def embedding_identity(model=None) -> dict:
    """Recorded in model_version: where the embedding came from and its dimensions."""
    data = embedding_source().as_dict()
    data.pop("path", None)
    data["vector_size"] = getattr(model, "vector_size", None) if model is not None else None
    return data
