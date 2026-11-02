"""Catalog tests: whitelist, default and thesis F1 values. No pickles needed (run in CI)."""

from pathlib import PurePosixPath

import pytest

from apps.analysis.services import model_catalog as mc
from apps.analysis.services.exceptions import UnknownModelError


def test_default_classifier_is_best_model_in_thesis():
    entry = mc.get_classifier_entry(mc.DEFAULT_CLASSIFIER_ID)

    assert entry.id == "m2-wordvector-tf5-svm"
    assert entry.available and entry.is_default and entry.is_best_for_algorithm
    assert (entry.f1_cv, entry.f1_test) == (0.6811, 0.6460)
    assert (entry.thesis_ref_cv, entry.thesis_ref_test) == ("Tabel 4.59", "Tabel 4.60")
    assert entry.relative_path == "character-classification/wordvector/m2/svm_pretrained_model.pkl"
    assert entry.bundle_keys == ("m2",)


def test_default_has_highest_cv_f1_of_all_entries():
    best = max(mc.CLASSIFIERS.values(), key=lambda e: e.f1_cv)
    assert best.feature_codes == ("TF5",) and best.algorithm_code == "svm"


@pytest.mark.parametrize("bad", ["", "../models/x.pkl", "/etc/passwd", "C:\\models\\svm.pkl",
                                 "character-classification/wordvector/m2/svm_pretrained_model.pkl",
                                 "M2-WORDVECTOR-TF5-SVM", None, 3])
def test_unknown_ids_are_rejected(bad):
    with pytest.raises(UnknownModelError):
        mc.get_classifier_entry(bad)


def test_unavailable_entries_are_rejected_unless_asked():
    entry_id = "m1-lexicon-tf1-tf3-knn"
    with pytest.raises(UnknownModelError):
        mc.get_classifier_entry(entry_id)
    assert mc.get_classifier_entry(entry_id, require_available=False).available is False


def test_catalog_size_and_availability():
    entries = list(mc.CLASSIFIERS.values())
    assert len(entries) == 6 + 18 + 6 + 42
    available = mc.available_classifiers()
    assert len(available) == 24
    assert all(e.feature_type == "wordvector" for e in available)
    assert not any(e.available for e in entries if e.feature_type == "lexicon")


def test_paths_are_relative_and_inside_classification_folder():
    for entry in mc.CLASSIFIERS.values():
        path = PurePosixPath(entry.relative_path)
        assert not path.is_absolute() and ".." not in path.parts and "\\" not in entry.relative_path
        assert path.parts[0] == "character-classification" and path.suffix == ".pkl"
        assert path.parts[1] == entry.feature_type and path.parts[2] == entry.variant


def test_m2_feature_mapping_matches_inspected_pickles():
    m2 = {e.algorithm_code: e.feature_codes for e in mc.CLASSIFIERS.values()
          if e.variant == "m2" and e.feature_type == "wordvector"}
    assert m2 == {"knn": ("TF4",), "dt": ("TF4",), "svm": ("TF5",), "gnb": ("TF5",), "mlp": ("TF5",), "rf": ("TF5",)}


def test_m1_bundle_keys_use_algorithm_name():
    entry = mc.get_classifier_entry("m1-wordvector-tf4-tf5-rf")
    assert entry.relative_path.endswith("wordvector/m1/TF4_TF5_pretrained_baseline_m1.pkl")
    assert entry.bundle_keys == ("Random Forest", "pretrained_model")
    assert entry.feature_codes == ("TF4", "TF5")


@pytest.mark.parametrize(("entry_id", "f1_cv", "f1_test"), [
    ("m2-wordvector-tf4-knn", 0.6666, 0.6451),
    ("m1-wordvector-tf4-knn", 0.6666, 0.6369),
    ("m1-wordvector-tf5-svm", 0.6811, 0.6366),
    ("m2-wordvector-tf5-mlp", 0.6447, 0.6596),
    ("m2-wordvector-tf5-gnb", 0.6190, 0.5932),
    ("m2-wordvector-tf4-dt", 0.6133, 0.6366),
    ("m1-wordvector-tf4-svm", 0.6642, None),  # not the best combination: no test F1 in the thesis
    ("m1-wordvector-tf4-tf5-svm", 0.6717, None),
    ("m1-lexicon-tf1-tf3-knn", 0.6378, 0.6304),
    ("m2-lexicon-tf1-tf2-tf3-gnb", 0.6351, 0.5975),
    ("m1-lexicon-tf3-svm", 0.5328, None),
])
def test_thesis_f1_values(entry_id, f1_cv, f1_test):
    entry = mc.CLASSIFIERS[entry_id]
    assert (entry.f1_cv, entry.f1_test) == (f1_cv, f1_test)


def test_best_entries_have_test_f1_and_others_not():
    for entry in mc.CLASSIFIERS.values():
        assert entry.f1_cv is not None
        assert (entry.f1_test is not None) == entry.is_best_for_algorithm
        assert (entry.thesis_ref_test is not None) == entry.is_best_for_algorithm


def test_ner_and_alias_defaults():
    assert mc.DEFAULT_NER_MODEL == "satuaner"
    assert set(mc.NER_MODELS) == {"satuaner", "crf1_baseline", "crf2_baseline", "svm_baseline", "hmm"}
    assert mc.DEFAULT_ALIAS_METHOD == "jaro-distance" and mc.DEFAULT_ALIAS_THRESHOLD == 0.85
    assert set(mc.ALIAS_METHODS) == {"ratcliff", "jaccard", "sorensen-dice", "jaro-distance", "jaro-winkler"}
    assert max(mc.ALIAS_METHODS.values(), key=lambda m: m.f1).id == mc.DEFAULT_ALIAS_METHOD


def test_validate_config_defaults_and_values():
    assert mc.validate_config() == mc.PipelineConfig()
    config = mc.validate_config("alias", "hmm", "jaccard", "0.9", "m1-wordvector-tf4-dt")
    assert config == mc.PipelineConfig("alias", "hmm", "jaccard", 0.9, "m1-wordvector-tf4-dt")
    assert config.runs_alias and not config.runs_roles


@pytest.mark.parametrize("kwargs", [
    {"task": "train"}, {"ner_model": "bert"}, {"alias_method": "levenshtein"},
    {"alias_threshold": 0.2}, {"alias_threshold": 1.5}, {"classifier_id": "m2-lexicon-tf1-tf3-knn"},
    {"classifier_id": "../../x.pkl"},
])
def test_validate_config_rejects_bad_values(kwargs):
    with pytest.raises(ValueError):
        mc.validate_config(**kwargs)


def test_classifier_groups_cover_every_entry_once():
    ids = [e.id for _key, entries in mc.classifier_groups() for e in entries]
    assert sorted(ids) == sorted(mc.CLASSIFIERS)
    assert mc.classifier_groups()[0][1][0].variant == "m2"
