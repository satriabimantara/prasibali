"""Validation and preprocessing of satua text, in the same order as the old web app and the test script.

The sentence separator produced by balinese-nlp is the literal two-character string backslash + n, not a newline.
"""

from __future__ import annotations

import functools
import unicodedata
from dataclasses import dataclass, field

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from .exceptions import PreprocessingError, TextValidationError

SENTENCE_SEP = "\\n"
MIN_SENTENCES = 11  # input limit used in the thesis (Bab 1.4); fewer only triggers a warning
MAX_NON_ASCII_LETTER_RATIO = 0.5  # above this the text is most likely Balinese script (aksara Bali)


@dataclass(frozen=True)
class PreprocessedStory:
    text: str  # preprocessed text, sentences separated by SENTENCE_SEP and ending with it
    sentences: list[str]
    warnings: list[str] = field(default_factory=list)

    @property
    def display_text(self) -> str:
        """Text shown with highlights; entity offsets refer to this string."""
        return " ".join(self.sentences)


@functools.lru_cache(maxsize=1)
def text_preprocessor():
    """One TextPreprocessor per process (it loads its dictionaries once)."""
    from balinese_nlp.textpreprocessor import TextPreprocessor

    return TextPreprocessor()


def validate_text(raw: str | None) -> str:
    """Return the stripped text or raise TextValidationError with a code and a user message."""
    text = (raw or "").strip()
    if not text:
        raise TextValidationError("empty", _("Enter the text of a satua to analyse."))
    limit = settings.ANALYSIS_MAX_CHARS
    if len(text) > limit:
        raise TextValidationError(
            "too_long",
            _("The text is too long. Enter at most %(limit)s characters.") % {"limit": f"{limit:,}".replace(",", ".")},
        )
    letters = [ch for ch in text if ch.isalpha()]
    non_ascii = sum(1 for ch in letters if ord(ch) > 127 and not _is_latin(ch))
    if letters and non_ascii / len(letters) > MAX_NON_ASCII_LETTER_RATIO:
        raise TextValidationError(
            "script",
            _("The text appears to use Balinese script. Enter the satua in Latin script; "
              "Balinese script support is coming soon."),
        )
    if "." not in text:
        raise TextValidationError(
            "no_sentences", _("The text has no sentences. End every sentence with a full stop (.)."),
        )
    return text


def _is_latin(ch: str) -> bool:
    """Accented Latin letters (é, ö) are fine: convert_ascii_sentence maps them to ASCII."""
    try:
        return unicodedata.name(ch).startswith("LATIN")
    except ValueError:
        return False


def preprocess_story(raw: str) -> PreprocessedStory:
    """Validate, then run the nine preprocessing steps (same order as scripts/test_pretrained_pipeline.py)."""
    text = validate_text(raw)
    try:
        tp = text_preprocessor()
        text = tp.convert_ascii_sentence(text)
        text = tp.normalize_words(text)
        text = tp.remove_tab_characters(text)
        text = tp.remove_special_punctuation(text)
        text = tp.remove_punctuation(text)
        text = tp.remove_exclamation_words(text)
        text = tp.add_enter_after_period_punctuation(text)
        text = tp.remove_leading_trailing_whitespace(text)
        text = tp.remove_whitespace_multiple(text)
    except Exception as exc:
        raise PreprocessingError(detail=repr(exc)) from exc

    # BaseModel.identify_characters drops the last element after splitting, so the text must end with a separator.
    if not text.rstrip().endswith(SENTENCE_SEP):
        text = f"{text.rstrip()}{SENTENCE_SEP}"
    sentences = [s.strip() for s in text.split(SENTENCE_SEP) if s.strip()]
    if not sentences:
        raise TextValidationError(
            "no_sentences", _("The text has no sentences. End every sentence with a full stop (.)."),
        )
    warnings = []
    if len(sentences) < MIN_SENTENCES:
        warnings.append(
            str(_("The text has fewer than %(n)s sentences, the minimum used in the thesis. "
                  "Results may be less reliable.") % {"n": MIN_SENTENCES})
        )
    return PreprocessedStory(text=text, sentences=sentences, warnings=warnings)


def preprocess_context(value) -> str:
    """Clean the grouped sentences of one character group before feature extraction.

    Legacy behaviour of the old web app (developer decision, Sesi 0): it filled the context column with case
    folding and then overwrote it with remove_stop_words(GroupedSentences), so case folding had no effect.
    Steps: remove stop words -> drop periods -> '-' to space -> strip. Same as scripts/test_pretrained_pipeline.py
    with its default LEGACY_PREPROCESS = True.
    """
    text = " ".join(map(str, value)) if isinstance(value, list | tuple) else str(value)
    text = text.replace(SENTENCE_SEP, " ")
    return text_preprocessor().remove_stop_words(text).replace(".", " ").replace("-", " ").strip()
