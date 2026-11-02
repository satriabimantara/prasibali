"""Text validation and preprocessing (balinese-nlp TextPreprocessor; no pickles needed)."""

from pathlib import Path

import pytest

from apps.analysis.services.exceptions import TextValidationError
from apps.analysis.services.preprocessing import (
    SENTENCE_SEP,
    preprocess_context,
    preprocess_story,
    validate_text,
)

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "src" / "apps" / "analysis" / "data" / "sample_satua"


@pytest.mark.parametrize(("text", "code"), [
    ("", "empty"),
    ("   \n ", "empty"),
    ("I Kancil ngajak I Kakua luas ka tukade", "no_sentences"),
    ("ᬓᬸᬝᬶᬮ. ᬓᬸᬝᬶᬮ.", "script"),
])
def test_validation_errors(text, code):
    with pytest.raises(TextValidationError) as info:
        validate_text(text)
    assert info.value.code == code
    assert str(info.value.user_message)


def test_too_long(settings):
    settings.ANALYSIS_MAX_CHARS = 50
    with pytest.raises(TextValidationError) as info:
        validate_text("Kacerita. " * 10)
    assert info.value.code == "too_long"


def test_accented_latin_is_accepted():
    assert validate_text("Ni Mésaba luas ka alasé.") == "Ni Mésaba luas ka alasé."


def test_preprocess_sample_satua():
    raw = (SAMPLE_DIR / "i_kancil_nulungin_i_kakua.txt").read_text(encoding="utf-8")
    story = preprocess_story(raw)

    assert story.text.endswith(SENTENCE_SEP)
    assert len(story.sentences) >= 5
    assert all(SENTENCE_SEP not in s and s == s.strip() for s in story.sentences)
    assert story.display_text == " ".join(story.sentences)
    assert all(ord(ch) < 128 for ch in story.text)


def test_short_text_gives_warning_not_error():
    story = preprocess_story("I Kancil luas ka tukade. Ditu ia nepukin I Kakua")
    assert len(story.sentences) == 2  # the last sentence without a full stop is kept
    assert story.warnings


def test_preprocess_context_is_legacy_without_case_folding():
    context = preprocess_context("I Kancil Ngajak I Kakua luas.\\n Ia ngalih amah-amahan.")
    assert "Kancil" in context  # case is kept (old web behaviour)
    assert "." not in context and "-" not in context and SENTENCE_SEP not in context
