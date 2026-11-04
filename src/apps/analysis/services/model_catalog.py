"""Static catalog of every model choice in PrasiBali, one entry per thesis experiment.

Users pick models only by catalog id; ids are validated against this whitelist on the server, and file paths are
derived from the entry, never from user input (unpickling can execute code).

Sources (thesis book, I Made Satria Bimantara, Universitas Udayana):
- Classifier F1 10-fold CV per feature combination: Lampiran 17 (summary of the best combinations: Tabel 4.56
  lexicon, Tabel 4.57 word vector, Tabel 4.59 overall). CV F1 belongs to algorithm + features, so M1 = M2.
- Classifier F1 on test data, only for the best combination per algorithm and feature type: Lampiran 15 (M1),
  Lampiran 16 and Tabel 4.60 (M2). Other combinations have no test F1 in the thesis -> None, shown as "–".
- NER: Tabel 4.18 (CV) and 4.19 (test, macro, M2). Alias clustering: Tabel 4.36/4.37 (M2 SatuaNER, threshold 0.85).
Numbers must never be invented; leave None when the thesis has none.

Pickle structure (scripts/test_pretrained_pipeline.py --inspect, 2 Nov 2026):
- wordvector/m1/<CODES>_pretrained_baseline_m1.pkl: dict keyed by algorithm name -> ["pretrained_model"] with
  "estimator" and, for TF4, "feature_extractor"["TF4"] (TfidfVectorizer). TF5 is not stored (built from FastText).
- wordvector/m2/<algo>_pretrained_model.pkl: {"m2": {"estimator", ["feature_extractor"]}}; knn/dt use TF4, the
  others TF5 (n_features_in_ 300).
- lexicon/*: reference the old `FeatureExtraction` module and cannot be unpickled -> available=False for v1.0.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from django.utils.translation import gettext_lazy as _

from .exceptions import UnknownModelError

# --------------------------------------------------------------------------- algorithms and features
ALGORITHMS = {  # code -> (name used as key in the M1 bundles, short label)
    "knn": ("K-Nearest Neighbor", "KNN"),
    "dt": ("Decision Tree", "DT"),
    "svm": ("Support Vector Machine", "SVM"),
    "gnb": ("Gaussian Naive Bayes", "GNB"),
    "rf": ("Random Forest", "RF"),
    "mlp": ("Multilayer Perceptron", "MLP"),
}
LEXICON_CODES = ("TF1", "TF2", "TF3")  # BaliSentiLex lexicon (TF1, TF2) and POS tag (TF3) features
WORDVECTOR_CODES = ("TF4", "TF5")  # TF4 = TF-IDF, TF5 = average FastText word embedding (300 dimensions)
FEATURE_TYPES = {"wordvector": _("Word vector"), "lexicon": _("Lexicon")}
VARIANTS = {
    "m2": _("M2: optimal configuration trained on all training data"),
    "m1": _("M1: optimal configuration trained on the best cross-validation fold"),
}

# --------------------------------------------------------------------------- thesis F1 values
# Word vector, F1 10-fold CV (Lampiran 17B).
WORDVECTOR_F1_CV = {
    "TF4": {"dt": 0.6133, "gnb": 0.6051, "knn": 0.6666, "mlp": 0.6343, "rf": 0.6526, "svm": 0.6642},
    "TF4_TF5": {"dt": 0.6129, "gnb": 0.6051, "knn": 0.6518, "mlp": 0.6215, "rf": 0.6493, "svm": 0.6717},
    "TF5": {"dt": 0.5961, "gnb": 0.6190, "knn": 0.6497, "mlp": 0.6447, "rf": 0.6775, "svm": 0.6811},
}
# Best word-vector feature per algorithm (Tabel 4.57); also the feature stored in each M2 file.
WORDVECTOR_BEST = {"knn": "TF4", "dt": "TF4", "svm": "TF5", "rf": "TF5", "gnb": "TF5", "mlp": "TF5"}
# Word vector, F1 on test data for the best feature (Lampiran 15 = M1; Tabel 4.60 / Lampiran 16 = M2).
WORDVECTOR_F1_TEST = {
    "m1": {"knn": 0.6369, "dt": 0.6188, "svm": 0.6366, "rf": 0.6270, "gnb": 0.5819, "mlp": 0.6121},
    "m2": {"knn": 0.6451, "dt": 0.6366, "svm": 0.6460, "rf": 0.6273, "gnb": 0.5932, "mlp": 0.6596},
}

# Lexicon, F1 10-fold CV (Lampiran 17A).
LEXICON_F1_CV = {
    "TF1": {"dt": 0.5952, "gnb": 0.6148, "knn": 0.5797, "mlp": 0.5852, "rf": 0.6030, "svm": 0.6131},
    "TF1_TF2": {"dt": 0.5883, "gnb": 0.6351, "knn": 0.6226, "mlp": 0.6065, "rf": 0.5909, "svm": 0.6082},
    "TF1_TF2_TF3": {"dt": 0.5784, "gnb": 0.6351, "knn": 0.6250, "mlp": 0.6229, "rf": 0.6138, "svm": 0.6038},
    "TF1_TF3": {"dt": 0.5605, "gnb": 0.6161, "knn": 0.6378, "mlp": 0.5768, "rf": 0.6184, "svm": 0.6235},
    "TF2": {"dt": 0.5687, "gnb": 0.6308, "knn": 0.6197, "mlp": 0.6124, "rf": 0.5782, "svm": 0.6098},
    "TF2_TF3": {"dt": 0.5678, "gnb": 0.6264, "knn": 0.6173, "mlp": 0.6066, "rf": 0.6062, "svm": 0.5995},
    "TF3": {"dt": 0.5393, "gnb": 0.5157, "knn": 0.5444, "mlp": 0.5110, "rf": 0.5522, "svm": 0.5328},
}
# Best lexicon combination per algorithm (Tabel 4.56); assumed to be the one stored in each M2 file (unverified).
LEXICON_BEST = {
    "knn": "TF1_TF3", "dt": "TF1", "svm": "TF1_TF3", "rf": "TF1_TF3", "gnb": "TF1_TF2_TF3", "mlp": "TF1_TF2_TF3",
}
LEXICON_F1_TEST = {
    "m1": {"knn": 0.6304, "dt": 0.5705, "svm": 0.5950, "rf": 0.5808, "gnb": 0.6096, "mlp": 0.6231},
    "m2": {"knn": 0.6166, "dt": 0.5492, "svm": 0.5655, "rf": 0.5716, "gnb": 0.5975, "mlp": 0.6480},
}

# Rule-based BaliSentiLex baseline, for captions only (no model to run).
BASELINE_RULE_BASED_F1 = {"cv": 0.5395, "test": 0.5148}

# --------------------------------------------------------------------------- classifier entries
CLASSIFICATION_DIR = "character-classification"
LABEL_ENCODER_PATH = "label-encoder/without_coreference_splitted_characterization.pkl"


@dataclass(frozen=True)
class ClassifierEntry:
    id: str
    variant: str  # "m1" | "m2"
    feature_type: str  # "wordvector" | "lexicon"
    feature_codes: tuple[str, ...]  # in file-name order, e.g. ("TF4", "TF5")
    algorithm: str  # full name, e.g. "Support Vector Machine"
    algorithm_code: str  # "svm"
    relative_path: str  # relative to PRETRAINED_MODELS_DIR, POSIX separators
    bundle_keys: tuple[str, ...]  # path inside the pickle to the dict holding "estimator"
    thesis_ref_cv: str
    thesis_ref_test: str | None
    f1_cv: float | None
    f1_test: float | None
    available: bool
    is_best_for_algorithm: bool

    @property
    def feature_label(self) -> str:
        return "+".join(self.feature_codes)

    @property
    def algorithm_label(self) -> str:
        return ALGORITHMS[self.algorithm_code][1]

    @property
    def uses_tf5(self) -> bool:
        return "TF5" in self.feature_codes

    @property
    def is_default(self) -> bool:
        return self.id == DEFAULT_CLASSIFIER_ID

    @property
    def is_thesis_best(self) -> bool:
        return self.id == THESIS_BEST_CLASSIFIER_ID

    def as_dict(self) -> dict:
        data = asdict(self)
        data["feature_codes"] = list(self.feature_codes)
        data["bundle_keys"] = list(self.bundle_keys)
        return data


def _entry(variant: str, feature_type: str, codes: str, algo: str) -> ClassifierEntry:
    wordvector = feature_type == "wordvector"
    best = (WORDVECTOR_BEST if wordvector else LEXICON_BEST)[algo] == codes
    f1_cv = (WORDVECTOR_F1_CV if wordvector else LEXICON_F1_CV)[codes][algo]
    f1_test = (WORDVECTOR_F1_TEST if wordvector else LEXICON_F1_TEST)[variant][algo] if best else None
    if best:
        ref_cv = "Tabel 4.59" if (wordvector and codes == "TF5" and algo == "svm") else (
            "Tabel 4.57" if wordvector else "Tabel 4.56")
        ref_test = "Lampiran 15" if variant == "m1" else ("Tabel 4.60" if wordvector else "Lampiran 16")
    else:
        ref_cv, ref_test = "Lampiran 17", None

    folder = f"{CLASSIFICATION_DIR}/{feature_type}/{variant}"
    if variant == "m1":
        path = f"{folder}/{codes}_pretrained_baseline_m1.pkl"
        keys = (ALGORITHMS[algo][0], "pretrained_model")
    else:
        path = f"{folder}/{algo}_pretrained_model.pkl"
        keys = ("m2",)
    return ClassifierEntry(
        id=f"{variant}-{feature_type}-{codes.lower().replace('_', '-')}-{algo}",
        variant=variant,
        feature_type=feature_type,
        feature_codes=tuple(codes.split("_")),
        algorithm=ALGORITHMS[algo][0],
        algorithm_code=algo,
        relative_path=path,
        bundle_keys=keys,
        thesis_ref_cv=ref_cv,
        thesis_ref_test=ref_test,
        f1_cv=f1_cv,
        f1_test=f1_test,
        # Lexicon pickles cannot be unpickled (old `FeatureExtraction` module): shown as "coming soon".
        available=wordvector,
        is_best_for_algorithm=best,
    )


def _build_catalog() -> dict[str, ClassifierEntry]:
    entries: list[ClassifierEntry] = []
    for algo in ALGORITHMS:  # M2: one file per algorithm, holding its best combination
        entries.append(_entry("m2", "wordvector", WORDVECTOR_BEST[algo], algo))
    for codes in WORDVECTOR_F1_CV:  # M1: one file per combination, holding all six algorithms
        for algo in ALGORITHMS:
            entries.append(_entry("m1", "wordvector", codes, algo))
    for algo in ALGORITHMS:
        entries.append(_entry("m2", "lexicon", LEXICON_BEST[algo], algo))
    for codes in LEXICON_F1_CV:
        for algo in ALGORITHMS:
            entries.append(_entry("m1", "lexicon", codes, algo))
    catalog = {entry.id: entry for entry in entries}
    if len(catalog) != len(entries):
        raise RuntimeError("Duplicate classifier ids in the model catalog")
    return catalog


CLASSIFIERS: dict[str, ClassifierEntry] = _build_catalog()

# Best model in the thesis: SVM + TF5 has the highest CV F1 (0.6811, Tabel 4.57/4.59), and M2 has the higher test
# F1 (0.6460 vs M1 0.6366, Tabel 4.60). Labelled "best in the thesis" in Mode Peneliti.
THESIS_BEST_CLASSIFIER_ID = "m2-wordvector-tf5-svm"
# Default for general users (developer decision, 4 Nov 2026): M2 KNN + TF4 (TF-IDF) gave better roles on the
# developer's test satua in Mode Peneliti. Thesis: CV F1 0.6666 (best word-vector feature for KNN, Tabel 4.57) and
# test F1 0.6451 (Tabel 4.60). It needs no FastText embedding.
DEFAULT_CLASSIFIER_ID = "m2-wordvector-tf4-knn"


def required_model_files() -> list[str]:
    """Pickles under PRETRAINED_MODELS_DIR that v1.0 loads: every available classifier file and the label encoder.

    Used by scripts/bundle_models.py (one-time upload to the server). FastText is not listed: it comes from
    PRETRAINED_MODELS_DIR/balinese-word-embedding/ when present, otherwise from Hugging Face (embeddings.py).
    """
    return sorted({entry.relative_path for entry in CLASSIFIERS.values() if entry.available} | {LABEL_ENCODER_PATH})


def get_classifier_entry(catalog_id: str, *, require_available: bool = True) -> ClassifierEntry:
    """Whitelist lookup. Raises UnknownModelError for anything that is not an exact catalog id."""
    entry = CLASSIFIERS.get(catalog_id) if isinstance(catalog_id, str) else None
    if entry is None:
        raise UnknownModelError(f"Unknown classifier id: {catalog_id!r}")
    if require_available and not entry.available:
        raise UnknownModelError(f"Classifier is not available: {catalog_id!r}")
    return entry


def available_classifiers() -> list[ClassifierEntry]:
    return [entry for entry in CLASSIFIERS.values() if entry.available]


def classifier_groups() -> list[tuple[str, list[ClassifierEntry]]]:
    """Entries grouped for the research panel: M2 word vector, M1 word vector, then lexicon (coming soon)."""
    order = [("m2", "wordvector"), ("m1", "wordvector"), ("m2", "lexicon"), ("m1", "lexicon")]
    entries = list(CLASSIFIERS.values())
    return [
        (f"{variant}-{kind}", [e for e in entries if (e.variant, e.feature_type) == (variant, kind)])
        for variant, kind in order
    ]


# --------------------------------------------------------------------------- NER and alias clustering
@dataclass(frozen=True)
class NerModel:
    id: str
    label: str
    f1_cv: float | None  # Tabel 4.18
    f1_test: float | None  # Tabel 4.19, macro F1 on test data, M2


NER_MODELS = {
    "satuaner": NerModel("satuaner", "SatuaNER (CRF + BPSO)", 0.954, 0.8353),
    "crf1_baseline": NerModel("crf1_baseline", "CRF-1", 0.9467, 0.8122),
    "crf2_baseline": NerModel("crf2_baseline", "CRF-2", 0.9518, 0.8262),
    "svm_baseline": NerModel("svm_baseline", "SVM", 0.947, 0.8072),
    "hmm": NerModel("hmm", "HMM", 0.932, 0.7312),
}
DEFAULT_NER_MODEL = "satuaner"


@dataclass(frozen=True)
class AliasMethod:
    id: str
    label: str
    f1: float | None  # Tabel 4.37: average F1 with M2 SatuaNER at threshold 0.85


ALIAS_METHODS = {
    "jaro-distance": AliasMethod("jaro-distance", "Jaro distance", 0.7172),
    "sorensen-dice": AliasMethod("sorensen-dice", "Sørensen–Dice", 0.7159),
    "jaro-winkler": AliasMethod("jaro-winkler", "Jaro–Winkler", 0.7097),
    "ratcliff": AliasMethod("ratcliff", "Ratcliff/Obershelp", 0.7076),
    "jaccard": AliasMethod("jaccard", "Jaccard", 0.7026),
}
# Best for SatuaNER M2 in the thesis (F1 0.7172, Tabel 4.36/4.37).
DEFAULT_ALIAS_METHOD = "jaro-distance"
DEFAULT_ALIAS_THRESHOLD = 0.85
ALIAS_THRESHOLD_MIN = 0.50
ALIAS_THRESHOLD_MAX = 1.00

# --------------------------------------------------------------------------- tasks and configuration
TASKS = {
    "full": _("Full pipeline: identification, grouping and roles"),
    "identify": _("Character identification only"),
    "alias": _("Identification and name grouping"),
    "role": _("Role classification"),
}
DEFAULT_TASK = "full"
ROLE_TASKS = frozenset({"full", "role"})
ALIAS_TASKS = frozenset({"full", "role", "alias"})


@dataclass(frozen=True)
class PipelineConfig:
    task: str = DEFAULT_TASK
    ner_model: str = DEFAULT_NER_MODEL
    alias_method: str = DEFAULT_ALIAS_METHOD
    alias_threshold: float = DEFAULT_ALIAS_THRESHOLD
    classifier_id: str = DEFAULT_CLASSIFIER_ID

    @property
    def runs_alias(self) -> bool:
        return self.task in ALIAS_TASKS

    @property
    def runs_roles(self) -> bool:
        return self.task in ROLE_TASKS

    def as_dict(self) -> dict:
        return asdict(self)


def validate_config(
    task: str | None = None,
    ner_model: str | None = None,
    alias_method: str | None = None,
    alias_threshold: float | str | None = None,
    classifier_id: str | None = None,
) -> PipelineConfig:
    """Build a PipelineConfig from (possibly user-supplied) values; None means the default. Raises ValueError."""
    task = task or DEFAULT_TASK
    if task not in TASKS:
        raise UnknownModelError(f"Unknown task: {task!r}")
    ner_model = ner_model or DEFAULT_NER_MODEL
    if ner_model not in NER_MODELS:
        raise UnknownModelError(f"Unknown NER model: {ner_model!r}")
    alias_method = alias_method or DEFAULT_ALIAS_METHOD
    if alias_method not in ALIAS_METHODS:
        raise UnknownModelError(f"Unknown alias method: {alias_method!r}")
    threshold = DEFAULT_ALIAS_THRESHOLD if alias_threshold in (None, "") else float(alias_threshold)
    if not ALIAS_THRESHOLD_MIN <= threshold <= ALIAS_THRESHOLD_MAX:
        raise ValueError(f"Alias threshold must be between {ALIAS_THRESHOLD_MIN} and {ALIAS_THRESHOLD_MAX}")
    classifier_id = get_classifier_entry(classifier_id or DEFAULT_CLASSIFIER_ID).id
    return PipelineConfig(task, ner_model, alias_method, round(threshold, 4), classifier_id)
