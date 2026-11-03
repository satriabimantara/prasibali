"""Fake pipeline results shared by the analysis view tests (no models needed)."""

from apps.analysis.services.pipeline import AnalysisResult, CharacterGroup, EntityMention, RoleResult

TEXT = "I Kancil luas ka tukade. Ditu ia nepukin I Kakua."


def fake_result(config, display_text="<script>alert(1)</script> I Kancil luas. Kancil nepukin I Kakua."):
    first = display_text.index("I Kancil")
    second = display_text.index("Kancil nepukin")
    kakua = display_text.index("I Kakua")
    split = display_text.index("luas.") + len("luas.")
    return AnalysisResult(
        config=config.as_dict(),
        display_text=display_text,
        sentences=[display_text[:split], display_text[split + 1:]],
        characters=["I Kakua", "I Kancil", "Kancil"],
        mentions=[
            EntityMention("I Kancil", "ANM", 0, first, first + len("I Kancil"), "Tokoh-1"),
            EntityMention("Kancil", "ANM", 1, second, second + len("Kancil"), "Tokoh-1"),
            EntityMention("I Kakua", "PNAME", 1, kakua, kakua + len("I Kakua"), "Tokoh-2"),
        ],
        groups=[CharacterGroup("Tokoh-1", 1, ["I Kancil", "Kancil"], 2, 1),
                CharacterGroup("Tokoh-2", 2, ["I Kakua"], 1, 2)],
        roles=[RoleResult("Tokoh-1", "Protagonis", "protagonis", 0.42, None, 8, None, True),
               RoleResult("Tokoh-2", "Antagonis", "antagonis", -0.3, None, 40, None, False)],
        timings={"preprocess": 0.1, "identify": 1.0, "alias": 0.1, "role": 0.5},
        model_version={"balinese_nlp": "2.4.2", "scikit_learn": "1.2.1", "ner_model": config.ner_model,
                       "alias": {"method": config.alias_method, "threshold": config.alias_threshold},
                       "classifier": {"id": config.classifier_id, "file": "svm_pretrained_model.pkl", "sha256": "abc"}},
    )
