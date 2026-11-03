"""The one-time model upload (scripts/bundle_models.py) holds exactly what v1.0 loads. No pickles needed (CI)."""

from apps.analysis.services import model_catalog as mc


def test_required_model_files_are_available_classifiers_and_label_encoder():
    files = mc.required_model_files()
    available = {entry.relative_path for entry in mc.CLASSIFIERS.values() if entry.available}
    assert set(files) == available | {mc.LABEL_ENCODER_PATH}
    assert mc.get_classifier_entry(mc.DEFAULT_CLASSIFIER_ID).relative_path in files
    assert mc.get_classifier_entry(mc.THESIS_BEST_CLASSIFIER_ID).relative_path in files
    assert not any("lexicon" in path or "balinese-word-embedding" in path for path in files)
    assert files == sorted(files) and len(files) == len(set(files))
