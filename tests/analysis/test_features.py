"""Feature extraction adaptor (ported from scripts/prasibali_models.py), with fakes instead of pickles."""

import numpy as np
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer

from apps.analysis.services import embeddings, features
from apps.analysis.services.exceptions import EmbeddingError, RoleClassificationError


class FakeWv(dict):
    pass


class FakeFastText:
    def __init__(self, size=3):
        self.vector_size = size
        self.wv = FakeWv(kancil=np.ones(size), siput=np.full(size, 3.0))


class FitTransformExtractor:
    """balinese-nlp style: fit(X) stores state, transform() takes no argument."""

    def __init__(self, pretrained_word_embedding=None):
        self.pretrained_word_embedding = pretrained_word_embedding

    def fit(self, X):
        self.X = X
        return self

    def transform(self):
        return np.array([[len(x)] for x in self.X], dtype=float)


CONTEXTS = ["kancil siput", "kancil", "tusing ada"]


def test_extract_model_entry_m2_wrapper_and_m1_keys():
    estimator = object()
    m2 = {"m2": {"estimator": estimator}}
    entry = features.extract_model_entry(m2, "Support Vector Machine", ("m2",))
    assert entry["estimator"] is estimator and entry["feature_extractor"] == {}

    m1 = {"K-Nearest Neighbor": {"fold_ke": "Fold-3",
                                 "pretrained_model": {"estimator": 1, "feature_extractor": {"TF4": 2}}},
          "Support Vector Machine": {"pretrained_model": {"estimator": estimator, "feature_extractor": {"TF4": 3}}}}
    entry = features.extract_model_entry(m1, "Support Vector Machine", ("Support Vector Machine", "pretrained_model"))
    assert entry["estimator"] is estimator
    # wrong keys fall back to the recursive search, which prefers the algorithm's own branch
    assert features.extract_model_entry(m1, "Support Vector Machine", ("nope",))["estimator"] is estimator


def test_extract_model_entry_unknown_structure():
    with pytest.raises(RoleClassificationError):
        features.extract_model_entry({"a": {"b": 1}}, "Support Vector Machine")


def test_select_extractors_tf5_missing_and_tf4_tf5():
    assert features.select_extractors({"feature_extractor": {}}, ["TF5"]) == [("TF5", None)]
    tfidf = object()
    selected = features.select_extractors({"feature_extractor": {"TF4": tfidf}}, ["TF4", "TF5"])
    assert selected == [("TF4", tfidf), ("TF5", None)]
    with pytest.raises(RoleClassificationError):
        features.select_extractors({"feature_extractor": {"TF1": 1, "TF2": 2}}, ["TF4"])


def test_run_extractor_shapes():
    tfidf = TfidfVectorizer().fit(["kancil siput", "siput"])
    matrix, how = features.run_extractor("TF4", tfidf, CONTEXTS, None)
    assert how == "transform(X)" and matrix.shape == (3, 2)

    model = FakeFastText()
    extractor = FitTransformExtractor()
    _, how = features.run_extractor("TF5", extractor, CONTEXTS, lambda: model)
    assert how == "fit(X).transform()" and extractor.pretrained_word_embedding is model

    matrix, how = features.run_extractor("TF5", None, CONTEXTS, lambda: model)
    assert matrix.shape == (3, 3)
    np.testing.assert_allclose(matrix[0], [2.0, 2.0, 2.0])  # mean of kancil (1) and siput (3)
    np.testing.assert_allclose(matrix[2], [0.0, 0.0, 0.0])  # no known word -> zeros

    with pytest.raises(EmbeddingError):
        features.run_extractor("TF5", None, CONTEXTS, None)


def test_featurize_concatenates_in_order_and_counts_known_terms():
    tfidf = TfidfVectorizer().fit(["kancil siput", "siput"])
    X, known, timings = features.featurize([("TF4", tfidf), ("TF5", None)], CONTEXTS, embedding_loader=FakeFastText)
    assert X.shape == (3, 2 + 3)
    assert known == [2, 1, 0]
    assert set(timings) == {"TF4", "TF5"}


def test_check_feature_count_and_tf5_dimensions():
    class Estimator:
        n_features_in_ = 5

    features.check_feature_count(Estimator(), np.zeros((1, 5)))
    with pytest.raises(RoleClassificationError):
        features.check_feature_count(Estimator(), np.zeros((1, 4)))

    tfidf = TfidfVectorizer().fit(["kancil siput"])
    assert features.tf5_dimensions(Estimator(), [("TF4", tfidf), ("TF5", None)]) == 3
    assert features.tf5_dimensions(Estimator(), [("TF4", tfidf)]) is None


def test_embedding_dimension_check():
    embeddings.check_dimension(FakeFastText(300), 300)
    embeddings.check_dimension(FakeFastText(50), None)
    with pytest.raises(EmbeddingError, match="TF5_FASTTEXT_FILENAME"):
        embeddings.check_dimension(FakeFastText(50), 300)


def test_embedding_source_prefers_local_file(settings, tmp_path):
    settings.TF5_HF_REPO_ID = ""
    settings.TF5_FASTTEXT_FILENAME = ""
    settings.PRETRAINED_MODELS_DIR = str(tmp_path)
    source = embeddings.embedding_source()
    assert (source.kind, source.repo_id, source.filename) == (
        "huggingface", embeddings.DEFAULT_TF5_REPO_ID, "300_fasttext_model.bin")

    folder = tmp_path / embeddings.LOCAL_EMBEDDING_DIR
    folder.mkdir()
    (folder / "300_fasttext_model.bin").write_bytes(b"")
    source = embeddings.embedding_source()
    assert source.kind == "local" and source.path == str(folder / "300_fasttext_model.bin")


def test_score_and_probability_for_svc_without_probability():
    from sklearn.svm import SVC

    X = np.array([[0.0], [1.0], [0.1], [0.9]])
    model = SVC().fit(X, [0, 1, 0, 1])
    scores, probabilities = features.score_and_probability(model, X)
    assert all(isinstance(s, float) for s in scores)
    assert probabilities == [None] * 4
