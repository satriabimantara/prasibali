"""
Utilitas bersama untuk skrip uji PrasiBali.ai: lokasi folder model, pemuatan pickle classifier
hasil eksperimen tesis, dan ekstraksi fitur teks (TF1-TF5).

Dipakai oleh scripts/check_env.py dan scripts/test_pretrained_pipeline.py. Aplikasi web punya
padanannya sendiri di src/apps/analysis/services/ (Sesi 3), yang sebaiknya mengikuti alur di sini.

Struktur folder pretrained-models (PRETRAINED_MODELS_DIR):
    character-classification/lexicon/m1/     TF1, TF1_TF3, ... (_pretrained_baseline_m1.pkl), 6 algoritma per file
    character-classification/lexicon/m2/     {knn,dt,svm,gnb,rf,mlp}_pretrained_model.pkl, 1 algoritma per file
    character-classification/wordvector/m1/  TF4, TF5, TF4_TF5 (_pretrained_baseline_m1.pkl)
    character-classification/wordvector/m2/  {knn,dt,svm,gnb,rf,mlp}_pretrained_model.pkl
    label-encoder/without_coreference_splitted_characterization.pkl

Keamanan: pickle bisa menjalankan kode saat dimuat. Muat hanya file model milik sendiri, dan jangan
pernah menerima path pickle dari input pengguna aplikasi.
"""
from __future__ import annotations

import functools
import hashlib
import inspect
import os
import pickle
import time
from collections.abc import Callable
from pathlib import Path

MODELS_ENV_VAR = "PRETRAINED_MODELS_DIR"
MODELS_REL = Path("_reference") / "old_web" / "website" / "balinarrativenlp" / "pretrained-models"
LABEL_ENCODER_REL = Path("label-encoder") / "without_coreference_splitted_characterization.pkl"

LEXICON_CODES = ("TF1", "TF2", "TF3")  # leksikon BaliSentiLex (TF1, TF2) dan POS tag (TF3)
WORDVECTOR_CODES = ("TF4", "TF5")  # TF4 = TF-IDF, TF5 = rata-rata word embedding FastText
ALGORITHM_FILE_PREFIX = {
    "K-Nearest Neighbor": "knn",
    "Decision Tree": "dt",
    "Support Vector Machine": "svm",
    "Gaussian Naive Bayes": "gnb",
    "Random Forest": "rf",
    "Multilayer Perceptron": "mlp",
}

# Model terbaik menurut buku tesis: SVM + TF5 (F1 rata-rata 10-fold CV 0,6811, Tabel 4.57/4.59);
# varian M2 karena F1 data uji 0,6460 > M1 0,6366 (Tabel 4.60).
DEFAULT_VARIANT = "m2"
DEFAULT_FEATURE = "TF5"
DEFAULT_CLASSIFIER = "Support Vector Machine"

# FastText bahasa Bali untuk TF5, diambil lewat balinese_nlp.embeddings.gensims.BaliFastText.
# Nilai bawaan dari contoh paket; WAJIB sama dengan file yang dipakai saat melatih pickle TF5.
# Tesis menyebut 300 dimensi, sedangkan nama file contoh berawalan "50_": pastikan lewat check_env.py
# (vector_size harus cocok dengan n_features_in_ model TF5).
TF5_REPO_ENV_VAR = "TF5_HF_REPO_ID"
TF5_FILENAME_ENV_VAR = "TF5_FASTTEXT_FILENAME"
DEFAULT_TF5_REPO_ID = "satriabimantara/balinese_pretrained_wordembedding"
DEFAULT_TF5_FILENAME = "50_fasttext_model.bin"
LOCAL_EMBEDDING_DIR = "balinese-word-embedding"  # di dalam PRETRAINED_MODELS_DIR
LOCAL_MARKER = "lokal"


class ModelError(Exception):
    """Kegagalan yang sudah dijelaskan untuk pengguna; traceback tidak diperlukan."""


# --------------------------------------------------------------------------- lokasi dan file
def env_value(root: Path, key: str) -> str | None:
    """Nilai variabel dari environment, lalu dari .env di akar repo (tanda kutip dibuang)."""
    value = os.environ.get(key)
    if value:
        return value
    env_file = root / ".env"
    if not env_file.is_file():
        return None
    for line in env_file.read_text(encoding="utf-8-sig").splitlines():
        name, sep, raw = line.strip().partition("=")
        if sep and name.strip() == key:
            raw = raw.strip()
            if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
                raw = raw[1:-1]
            return raw or None
    return None


def resolve_models_dir(root: Path, explicit: str | None = None) -> tuple[Path, str]:
    """Folder pretrained-models beserta sumbernya: argumen, PRETRAINED_MODELS_DIR, lalu path bawaan."""
    if explicit:
        return Path(explicit), "--models-dir"
    value = env_value(root, MODELS_ENV_VAR)
    if value:
        return Path(value), MODELS_ENV_VAR
    return root / MODELS_REL, "path bawaan"


def fingerprint(path: Path) -> str:
    """Hash SHA-256 pendek, sama dengan identitas model yang disimpan aplikasi di model_version."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def unpickle(path: Path):
    try:
        with path.open("rb") as handle:
            return pickle.load(handle)
    except ModuleNotFoundError as exc:
        raise ModelError(f"{path.name} merujuk modul '{exc.name}' yang tidak ada di environment ini") from exc


def describe(obj) -> str:
    cls = type(obj)
    return f"{cls.__module__}.{cls.__qualname__}"


# --------------------------------------------------------------------------- pemilihan bundle
def parse_feature_codes(text: str) -> list[str]:
    """'TF4_TF5', 'TF4+TF5', atau 'tf5' -> ['TF4', 'TF5'] / ['TF5']."""
    codes = [part.strip().upper() for part in text.replace("+", "_").split("_") if part.strip()]
    unknown = [code for code in codes if code not in LEXICON_CODES + WORDVECTOR_CODES]
    if not codes or unknown:
        raise ModelError(f"Kode fitur tidak dikenal: {text!r}. Pilihan: TF1-TF5, digabung dengan _ (mis. TF4_TF5)")
    return codes


def feature_folder(codes: list[str]) -> str:
    if all(code in LEXICON_CODES for code in codes):
        return "lexicon"
    if all(code in WORDVECTOR_CODES for code in codes):
        return "wordvector"
    raise ModelError("Gabungan fitur leksikon + word vector (ensemble) tidak tersedia sebagai pickle")


def bundle_path(models_dir: Path, variant: str, codes: list[str], classifier_name: str) -> Path:
    """M1: satu file per kombinasi fitur berisi 6 algoritma. M2: satu file per algoritma."""
    folder = models_dir / "character-classification" / feature_folder(codes) / variant
    if variant == "m1":
        exact = folder / f"{'_'.join(codes)}_pretrained_baseline_m1.pkl"
    elif variant == "m2":
        prefix = ALGORITHM_FILE_PREFIX.get(classifier_name)
        if prefix is None:
            raise ModelError(f"Algoritma tidak dikenal: {classifier_name!r}. Pilihan: {list(ALGORITHM_FILE_PREFIX)}")
        exact = folder / f"{prefix}_pretrained_model.pkl"
    else:
        raise ModelError(f"Varian tidak dikenal: {variant!r} (pilihan: m1, m2)")
    if exact.is_file():
        return exact
    available = sorted(p.name for p in folder.glob("*.pkl")) if folder.is_dir() else []
    raise ModelError(f"Pickle tidak ditemukan: {exact}. Tersedia di folder itu: {available}")


def _structure(obj, depth: int = 4, indent: int = 0) -> str:
    """Pohon kunci dict (maks. `depth` tingkat) untuk pesan galat, supaya struktur pickle terlihat."""
    pad = "  " * indent
    if not isinstance(obj, dict):
        return f"{describe(obj)}"
    if depth == 0:
        return f"dict({len(obj)} kunci)"
    lines = []
    for key, value in list(obj.items())[:12]:
        lines.append(f"\n{pad}  {key!r}: {_structure(value, depth - 1, indent + 1)}")
    return "dict:" + "".join(lines)


def _find_entry(obj, classifier_name: str, depth: int = 5):
    """Telusuri dict bertingkat; dahulukan cabang bernama algoritma atau 'pretrained_model'."""
    if not isinstance(obj, dict) or depth == 0:
        return None
    if "estimator" in obj:
        return obj
    preferred = [k for k in obj if k == classifier_name or k == "pretrained_model"]
    for key in preferred + [k for k in obj if k not in preferred]:
        found = _find_entry(obj[key], classifier_name, depth - 1)
        if found is not None:
            return found
    return None


def extract_model_entry(bundle, classifier_name: str) -> dict:
    """Cari dict berisi 'estimator' (dan 'feature_extractor' bila ada).

    M1 terverifikasi: bundle[nama_algoritma]['pretrained_model']. M2 dibungkus kunci 'm2' (terlihat
    2 Nov), jadi seluruh pohon dict ditelusuri. 'feature_extractor' yang tidak disimpan diisi {}
    (cukup untuk TF5 yang dibangun dari model FastText).
    """
    entry = _find_entry(bundle, classifier_name)
    if entry is None:
        raise ModelError(
            f"Struktur pickle tidak dikenali untuk '{classifier_name}': {_structure(bundle)}\n"
            "    Kirim pohon ini ke pengembang atau jalankan test_pretrained_pipeline.py --inspect."
        )
    if "feature_extractor" not in entry:
        entry = {**entry, "feature_extractor": {}}
    return entry


def select_extractors(entry: dict, codes: list[str]) -> list[tuple[str, object]]:
    """Ambil ekstraktor untuk tiap kode fitur, dengan urutan sama seperti nama file (mis. TF4 lalu TF5)."""
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
            # TF5 cukup ditentukan oleh model FastText, sehingga boleh tidak disimpan di pickle.
            selected.append((code, None))
        elif len(codes) == 1 and len(extractors) == 1:
            key, value = next(iter(extractors.items()))
            selected.append((str(key), value))
        else:
            raise ModelError(f"Ekstraktor fitur {code} tidak ada. Kunci feature_extractor: {list(extractors)}")
    return selected


def find_encoder(obj):
    """Cari objek LabelEncoder. Jalur yang diketahui: ['train']['y_encoder']."""
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


def load_encoder(models_dir: Path, explicit: str | None = None):
    path = Path(explicit) if explicit else models_dir / LABEL_ENCODER_REL
    if not path.is_file():
        raise ModelError(f"Label encoder tidak ditemukan: {path}")
    encoder = find_encoder(unpickle(path))
    if encoder is None:
        raise ModelError(f"Objek label encoder tidak ditemukan di dalam {path.name}")
    return path, encoder


# --------------------------------------------------------------------------- word embedding (TF5)
def embedding_config(root: Path) -> tuple[str, str]:
    """(repo, nama file) FastText. Bila file itu ada di <PRETRAINED_MODELS_DIR>/balinese-word-embedding/
    (atau TF5_FASTTEXT_FILENAME berupa path file), dipakai file lokal: (LOCAL_MARKER, path lengkap)."""
    repo_id = env_value(root, TF5_REPO_ENV_VAR) or DEFAULT_TF5_REPO_ID
    filename = env_value(root, TF5_FILENAME_ENV_VAR) or DEFAULT_TF5_FILENAME
    models_dir, _ = resolve_models_dir(root)
    for candidate in (Path(filename), models_dir / LOCAL_EMBEDDING_DIR / filename):
        if candidate.is_file():
            return LOCAL_MARKER, str(candidate)
    return repo_id, filename


def local_embedding_files(root: Path) -> list[str]:
    models_dir, _ = resolve_models_dir(root)
    folder = models_dir / LOCAL_EMBEDDING_DIR
    return sorted(p.name for p in folder.glob("*.bin")) if folder.is_dir() else []


@functools.lru_cache(maxsize=2)
def load_fasttext(repo_id: str, filename: str):
    """Muat FastText bahasa Bali (sekali per proses): file lokal lewat gensim, atau Hugging Face.

    Hugging Face memakai interface paket:
        BaliFastText(huggingface_repo_ID=..., pretrained_model_bin_filename=...).load_pretrained_model()
    """
    if repo_id == LOCAL_MARKER:
        try:
            from gensim.models import FastText

            return FastText.load(filename)  # file milik sendiri; gensim memakai pickle
        except Exception as exc:  # noqa: BLE001
            raise ModelError(f"Gagal memuat FastText lokal {filename}: {exc!r}") from exc
    try:
        from balinese_nlp.embeddings.gensims import BaliFastText
    except ImportError as exc:
        raise ModelError(f"balinese_nlp.embeddings.gensims.BaliFastText tidak bisa diimpor: {exc!r}") from exc
    try:
        return BaliFastText(huggingface_repo_ID=repo_id, pretrained_model_bin_filename=filename).load_pretrained_model()
    except Exception as exc:  # noqa: BLE001 - jaringan, token, atau nama file
        raise ModelError(f"Gagal memuat FastText {repo_id}/{filename} dari Hugging Face: {exc!r}") from exc


def average_word_vectors(model, contexts: list[str]):
    """Rata-rata word vector per konteks: TF5 pada tesis.

    Memakai WordEmbeddingFeatureExtraction dari balinese-nlp bila tersedia, agar identik dengan saat
    pelatihan. Salinan di bawah hanya cadangan (mis. untuk test tanpa paket) dan meniru baris per baris:
    kata dipisah spasi, hanya kata yang ada di model.wv, nol bila tidak ada kata yang dikenal.
    """
    import numpy as np

    try:
        from balinese_nlp.feature_extractor.narratives.characterclassification.WordEmbeddingFeatureExtraction import (
            WordEmbeddingFeatureExtraction,
        )
    except ImportError:
        WordEmbeddingFeatureExtraction = None  # noqa: N806
    if WordEmbeddingFeatureExtraction is not None:
        return WordEmbeddingFeatureExtraction(pretrained_word_embedding=model).fit(list(contexts)).transform()
    rows = []
    for sentence in contexts:
        vectors = [model.wv[word] for word in sentence.split() if word in model.wv]
        rows.append(sum(vectors) / len(vectors) if vectors else np.zeros(model.vector_size))
    return np.array(rows)


def is_word_embedding_model(obj) -> bool:
    return hasattr(obj, "wv") and hasattr(obj, "vector_size")


# --------------------------------------------------------------------------- ekstraksi fitur
def _transform_takes_input(extractor) -> bool:
    """True untuk gaya scikit-learn transform(X); False untuk gaya balinese-nlp fit(X).transform()."""
    try:
        params = inspect.signature(extractor.transform).parameters.values()
    except (TypeError, ValueError):
        return True
    return any(p.default is inspect.Parameter.empty and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
               for p in params)


def extractor_style(obj) -> str:
    """Keterangan singkat cara pakai ekstraktor, untuk --inspect dan check_env."""
    if callable(getattr(obj, "transform", None)):
        return "transform(X)" if _transform_takes_input(obj) else "fit(X).transform()"
    if is_word_embedding_model(obj):
        return "model word embedding"
    return "tanpa transform"


def run_extractor(code: str, extractor, contexts: list[str], embedding_loader: Callable[[], object] | None):
    """Jalankan satu ekstraktor dan kembalikan (matriks, keterangan cara ekstraksi).

    Bentuk yang didukung:
      1. scikit-learn (mis. TfidfVectorizer untuk TF4): extractor.transform(contexts)
      2. kelas balinese-nlp (WordEmbedding/Lexicon/POSTagFeatureExtraction): extractor.fit(contexts).transform()
         Bila WordEmbeddingFeatureExtraction tersimpan tanpa model embedding, model dimuat dari Hugging Face.
      3. model gensim (punya .wv dan .vector_size): dirata-rata seperti WordEmbeddingFeatureExtraction
      4. TF5 tanpa ekstraktor tersimpan (None/string): FastText dimuat dari Hugging Face lalu dirata-rata
    """
    transform = getattr(extractor, "transform", None)
    if callable(transform) and _transform_takes_input(extractor):
        return extractor.transform(contexts), "transform(X)"
    if callable(transform) and callable(getattr(extractor, "fit", None)):
        if hasattr(extractor, "pretrained_word_embedding") and not is_word_embedding_model(extractor.pretrained_word_embedding):
            if embedding_loader is None:
                raise ModelError(f"Ekstraktor {code} butuh model word embedding, tetapi pemuat embedding tidak diberikan")
            extractor.pretrained_word_embedding = embedding_loader()
        return extractor.fit(list(contexts)).transform(), "fit(X).transform()"
    if is_word_embedding_model(extractor):
        return average_word_vectors(extractor, contexts), "rata-rata word vector (model di pickle)"
    if code == "TF5" and (extractor is None or isinstance(extractor, str)):
        if embedding_loader is None:
            raise ModelError("Fitur TF5 butuh FastText dari Hugging Face, tetapi pemuat embedding tidak diberikan")
        return average_word_vectors(embedding_loader(), contexts), "rata-rata word vector (FastText Hugging Face)"
    raise ModelError(
        f"Ekstraktor {code} ({describe(extractor)}) tidak dikenali. Jalankan "
        "`python scripts/test_pretrained_pipeline.py --inspect` dan kirim hasilnya."
    )


def featurize(
    selected: list[tuple[str, object]],
    contexts: list[str],
    log: Callable[[str], None] = print,
    embedding_loader: Callable[[], object] | None = None,
):
    """Ubah konteks kalimat menjadi matriks fitur; blok tiap kode fitur digabung berdampingan.

    Mengembalikan (X, known_terms): known_terms = jumlah term TF-IDF yang dikenal per konteks,
    atau None bila tidak ada ekstraktor TF-IDF.

    Catatan: ekstraktor gaya balinese-nlp menyimpan state di fit(); jangan dipakai bersamaan oleh
    beberapa thread (Gunicorn worker sync aman).
    """
    import numpy as np

    blocks, known_terms = [], None
    for code, extractor in selected:
        started = time.perf_counter()
        matrix, how = run_extractor(code, extractor, contexts, embedding_loader)
        matrix = matrix.toarray() if hasattr(matrix, "toarray") else np.asarray(matrix, dtype=float)
        if matrix.ndim != 2 or matrix.shape[0] != len(contexts):
            raise ModelError(f"Keluaran ekstraktor {code} berbentuk {matrix.shape}, seharusnya ({len(contexts)}, n)")
        log(f"  Fitur {code}: {matrix.shape[1]} dimensi, {how}, {time.perf_counter() - started:.1f} dtk")
        if hasattr(extractor, "vocabulary_"):
            known_terms = [int(n) for n in (matrix != 0).sum(axis=1)]
        blocks.append(matrix)
    features = np.hstack(blocks) if len(blocks) > 1 else blocks[0]
    return features, known_terms


def check_feature_count(estimator, features) -> None:
    expected = getattr(estimator, "n_features_in_", None)
    if expected is not None and features.shape[1] != expected:
        raise ModelError(
            f"Jumlah fitur {features.shape[1]} tidak sama dengan yang diharapkan model ({expected}). "
            "Kombinasi atau urutan fitur kemungkinan berbeda dari saat pelatihan."
        )


def score_and_probability(estimator, features) -> tuple[list, list]:
    """Skor decision_function (bila ada) dan probabilitas kelas terpilih (bila model mendukung)."""
    import numpy as np

    n = features.shape[0]
    scores: list = [None] * n
    probabilities: list = [None] * n
    if callable(getattr(estimator, "decision_function", None)):
        raw = np.asarray(estimator.decision_function(features))
        scores = [round(float(v if raw.ndim == 1 else np.max(v)), 4) for v in raw]
    if callable(getattr(estimator, "predict_proba", None)):
        try:
            probabilities = [round(float(np.max(row)), 4) for row in estimator.predict_proba(features)]
        except Exception:  # noqa: BLE001 - mis. SVC tanpa probability=True
            pass
    return scores, probabilities
