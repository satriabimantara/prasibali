import pytest


@pytest.mark.model
def test_label_encoder_is_present(models_dir):
    """Runs only where the thesis pickles are mounted; skipped in CI. Does not unpickle anything."""
    encoder = models_dir / "label-encoder" / "without_coreference_splitted_characterization.pkl"
    assert encoder.is_file()


@pytest.mark.model
def test_classifier_folders_are_present(models_dir):
    base = models_dir / "character-classification"
    for sub in ("lexicon/m1", "lexicon/m2", "wordvector/m1", "wordvector/m2"):
        assert (base / sub).is_dir(), sub
