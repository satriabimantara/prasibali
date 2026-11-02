"""End-to-end pipeline with the real thesis pickles and FastText. Skipped where PRETRAINED_MODELS_DIR is missing.

The default configuration must give exactly the same result as scripts/test_pretrained_pipeline.py (the flow
verified against the real models): same characters, alias groups, labels and decision scores.
"""

from pathlib import Path

import pytest

from apps.analysis.services import embeddings, model_catalog
from apps.analysis.services.pipeline import classify_roles, run_full_pipeline
from apps.analysis.services.preprocessing import preprocess_story

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE = REPO_ROOT / "_reference" / "sample_satua" / "raw text" / "I Siput lawan I Kancil.txt"

pytestmark = [
    pytest.mark.model,
    pytest.mark.skipif(not SAMPLE.is_file(), reason="sample satua from the thesis dataset is not available"),
]


@pytest.fixture(scope="module")
def raw_text():
    import test_pretrained_pipeline as script

    return script.read_text(SAMPLE)


@pytest.fixture(scope="module")
def app_result(raw_text):
    return run_full_pipeline(raw_text)


@pytest.fixture(scope="module")
def script_result(raw_text):
    """Run the script's own functions with its default configuration (M2, TF5, SVM, legacy preprocessing)."""
    import prasibali_models as pm
    import test_pretrained_pipeline as script
    from django.conf import settings

    assert script.LEGACY_PREPROCESS is True
    tp, text, sentences = script.preprocess_story(raw_text)
    _model, characters = script.identify_characters("satuaner", text, sentences)
    groups = script.cluster_aliases(characters, "jaro-distance", 0.85)
    estimator, selected, encoder, scaler = script.load_classifier(
        Path(settings.PRETRAINED_MODELS_DIR), pm.DEFAULT_VARIANT, [pm.DEFAULT_FEATURE], pm.DEFAULT_CLASSIFIER, None,
    )
    frame = script.group_sentences(sentences, groups)
    # Same FastText file (local first, then Hugging Face); reuse the app's cached copy to avoid loading it twice.
    roles = script.classify_roles(frame, groups, tp, estimator, selected, encoder, embeddings.load_fasttext,
                                  scaler=scaler)
    return {"characters": characters, "groups": groups, "roles": roles}


def test_default_pipeline_matches_script(app_result, script_result):
    assert app_result.config == model_catalog.PipelineConfig().as_dict()
    assert app_result.characters == script_result["characters"]
    assert {g.group_id: g.aliases for g in app_result.groups} == script_result["groups"]
    assert [(r.group_id, r.role, r.decision_score, r.context_words) for r in app_result.roles] == [
        (r["group"], r["role"], r["decision_score"], r["context_words"]) for r in script_result["roles"]
    ]


def test_mentions_have_labels_and_positions(app_result):
    assert app_result.mentions
    labels = {"PNAME", "ANM", "GODS", "ADJ", "OBJ"}
    for mention in app_result.mentions:
        assert mention.label in labels
        span = app_result.display_text[mention.start:mention.end]
        # A name continued by an I- tag after O (package rule) spans the words in between.
        words = mention.text.split()
        assert span == mention.text or (span.startswith(words[0]) and span.endswith(words[-1]))
        assert mention.text in app_result.characters
    grouped = [m for m in app_result.mentions if m.group_id]
    assert grouped and sum(g.mention_count for g in app_result.groups) == len(grouped)


def test_model_version_is_complete(app_result):
    version = app_result.model_version
    assert version["balinese_nlp"] == "2.4.2" and version["scikit_learn"] == "1.2.1"
    assert version["ner_model"] == "satuaner"
    assert version["alias"] == {"method": "jaro-distance", "threshold": 0.85}
    classifier = version["classifier"]
    assert classifier["id"] == model_catalog.DEFAULT_CLASSIFIER_ID
    assert classifier["file"] == "svm_pretrained_model.pkl" and len(classifier["sha256"]) == 12
    assert classifier["classes"] == ["Antagonis", "Protagonis"]
    assert classifier["embedding"]["vector_size"] == 300
    assert set(app_result.timings) == {"preprocess", "identify", "alias", "role"}
    assert app_result.roles[0].role_key in {"protagonis", "antagonis"}
    assert all(r.probability is None for r in app_result.roles)  # SVC without probability=True


def test_identify_only_task(raw_text):
    result = run_full_pipeline(raw_text, model_catalog.validate_config(task="identify"))
    assert result.characters and not result.groups and not result.roles
    assert "alias" not in result.model_version and "classifier" not in result.model_version


@pytest.mark.parametrize("entry", sorted(model_catalog.available_classifiers(), key=lambda e: e.relative_path),
                         ids=lambda e: e.id)
def test_every_available_classifier_runs(entry, raw_text, app_result):
    story = preprocess_story(raw_text)
    groups = {g.group_id: g.aliases for g in app_result.groups}
    roles, info = classify_roles(story, groups, entry.id)
    assert info["id"] == entry.id
    assert [r.group_id for r in roles] == list(groups)
    assert {r.role for r in roles} <= {"Protagonis", "Antagonis"}
