"""Context sentences per character group, via balinese-nlp RuleBasedSentenceGrouping.

Side effect handled here: RuleBasedSentenceGrouping.__init__ creates a folder at
os.path.join(os.path.dirname(os.getcwd()), path_saved_file), "saved_file" by default, i.e. next to the working
directory, and prints a line. os.path.join discards the first part when the second is absolute, so passing an
absolute, writable folder (BALINESE_NLP_WORK_DIR) keeps the repo and read-only container folders clean. Nothing
is written into that folder because .save() is never called.
"""

from __future__ import annotations

import contextlib
import functools
import io
import tempfile
from pathlib import Path

from django.conf import settings


@functools.lru_cache(maxsize=4)
def _ensure_dir(path: str) -> str:
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def work_dir() -> str:
    default = Path(tempfile.gettempdir()) / "prasibali" / "saved_file"
    configured = getattr(settings, "BALINESE_NLP_WORK_DIR", "") or str(default)
    return _ensure_dir(str(Path(configured).resolve()))


def group_sentences(sentences: list[str], groups: dict[str, list[str]]):
    """DataFrame with one row per group (CharactersID, AliasCharacters, GroupedSentences), in `groups` order."""
    from balinese_nlp.quoteattribution.rule_based import RuleBasedSentenceGrouping

    with contextlib.redirect_stdout(io.StringIO()):
        grouping = RuleBasedSentenceGrouping(add_characterization_column=False, path_saved_file=work_dir())
    frame = grouping.fit(sentences=sentences, characters_alias_clustering=groups).predict()
    return frame.reset_index(drop=True)
