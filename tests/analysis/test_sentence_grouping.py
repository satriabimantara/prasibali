"""RuleBasedSentenceGrouping must not create saved_file next to the working directory."""

from apps.analysis.services import sentence_grouping


def test_grouping_uses_configured_work_dir(settings, tmp_path, monkeypatch):
    cwd = tmp_path / "repo" / "src"
    cwd.mkdir(parents=True)
    monkeypatch.chdir(cwd)
    settings.BALINESE_NLP_WORK_DIR = str(tmp_path / "work")

    frame = sentence_grouping.group_sentences(
        ["I Kancil luas ka tukade.", "I Kakua ngoyong di tukade.", "Ia matakon."],
        {"Tokoh-1": ["I Kancil"], "Tokoh-2": ["I Kakua", "Kakua"]},
    )

    assert list(frame["CharactersID"]) == ["Tokoh-1", "Tokoh-2"]
    assert frame.loc[1, "GroupedSentences"] == "I Kakua ngoyong di tukade."
    assert (tmp_path / "work").is_dir()
    assert not (tmp_path / "repo" / "saved_file").exists()
    assert not (cwd / "saved_file").exists()
    assert list((tmp_path / "work").iterdir()) == []  # nothing written per request
