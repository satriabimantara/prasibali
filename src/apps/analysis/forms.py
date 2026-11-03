"""Analysis form. Every model choice comes from the catalog (services/model_catalog.py), never from templates."""

from django import forms
from django.conf import settings
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from .presenters import f1
from .services import model_catalog as mc
from .services.exceptions import TextValidationError, UnknownModelError
from .services.preprocessing import validate_text

MODES = (("simple", gettext_lazy("General user")), ("advanced", gettext_lazy("Advanced")))

# Text features (thesis Tabel 3.10).
FEATURE_DESCRIPTIONS = {
    "TF1": gettext_lazy("basic BaliSentiLex lexicon features (total positive and negative synset scores)"),
    "TF2": gettext_lazy("additional lexicon features (word counts and polarity scores per word class)"),
    "TF3": gettext_lazy("POS tag features (share of nouns, adjectives, adverbs and verbs)"),
    "TF4": gettext_lazy("TF-IDF"),
    "TF5": gettext_lazy("average Balinese FastText word embedding (300 dimensions)"),
}


def tags_for(entry: mc.ClassifierEntry) -> list[str]:
    tags = []
    if entry.is_default:
        tags += [_("default"), _("recommended")]
    if entry.is_thesis_best:
        tags.append(_("best in the thesis"))
    if not entry.available:
        tags.append(_("coming soon"))
    return tags


def f1_cv_text(entry: mc.ClassifierEntry) -> str:
    return _("Macro F1 CV %(f1)s (%(ref)s)") % {"f1": f1(entry.f1_cv), "ref": entry.thesis_ref_cv}


def f1_test_text(entry: mc.ClassifierEntry) -> str:
    if entry.f1_test is None:
        return _("macro F1 test –")
    return _("macro F1 test %(f1)s (%(ref)s)") % {"f1": f1(entry.f1_test), "ref": entry.thesis_ref_test}


def classifier_label(entry: mc.ClassifierEntry) -> str:
    """One-line description of a catalog entry (history detail, plain-select fallback, tests)."""
    return " · ".join([entry.algorithm_label, entry.feature_label, f1_cv_text(entry), f1_test_text(entry),
                       *tags_for(entry)])


def research_catalog() -> dict:
    """Data for the cascaded classifier picker (variant -> feature type -> feature codes -> algorithm)."""
    entries = []
    for entry in mc.CLASSIFIERS.values():
        entries.append({
            "id": entry.id,
            "variant": entry.variant,
            "featureType": entry.feature_type,
            "codes": entry.feature_label,
            "algorithm": entry.algorithm_code,
            "algorithmLabel": entry.algorithm_label,
            "algorithmName": entry.algorithm,
            "available": entry.available,
            "isDefault": entry.is_default,
            "isThesisBest": entry.is_thesis_best,
            "isBestForAlgorithm": entry.is_best_for_algorithm,
            "f1Cv": f1(entry.f1_cv),
            "refCv": entry.thesis_ref_cv,
            "f1Test": f1(entry.f1_test),
            "refTest": entry.thesis_ref_test or "",
            "tags": tags_for(entry),
            "score": _("decision_function (distance to the hyperplane, not a probability)")
            if entry.algorithm_code == "svm" else _("estimated probability (predict_proba)"),
        })
    return {
        "entries": entries,
        "variants": [{"id": key, "label": key.upper(), "description": str(text)} for key, text in mc.VARIANTS.items()],
        "featureTypes": [{"id": key, "label": str(text)} for key, text in mc.FEATURE_TYPES.items()],
        "features": {code: str(text) for code, text in FEATURE_DESCRIPTIONS.items()},
        "defaultId": mc.DEFAULT_CLASSIFIER_ID,
        "text": {
            "comingSoon": _("coming soon"),
            "f1Cv": _("macro F1 CV"),
            "f1Test": _("test"),
            "noTest": _("The thesis tests only the best feature combination of each algorithm on the test data."),
        },
        "baseline": _("Rule-based BaliSentiLex baseline for comparison: F1 CV %(cv)s, F1 test %(test)s.") % {
            "cv": f1(mc.BASELINE_RULE_BASED_F1["cv"]), "test": f1(mc.BASELINE_RULE_BASED_F1["test"])},
    }


class AnalysisForm(forms.Form):
    text = forms.CharField(
        label=gettext_lazy("Satua text"),
        required=False,  # validate_text() gives the specific message
        widget=forms.Textarea(attrs={"rows": 12, "lang": "ban", "spellcheck": "false"}),
        help_text=gettext_lazy("Balinese text in Latin script. End every sentence with a full stop."),
    )
    mode = forms.ChoiceField(choices=MODES, initial="simple", required=False, widget=forms.HiddenInput)
    task = forms.ChoiceField(label=gettext_lazy("What to analyse"), choices=list(mc.TASKS.items()),
                             initial=mc.DEFAULT_TASK, widget=forms.Select(attrs={"x-model": "task"}))
    ner_model = forms.ChoiceField(label=gettext_lazy("(i) Character identification model"),
                                  initial=mc.DEFAULT_NER_MODEL, required=False)
    alias_method = forms.ChoiceField(label=gettext_lazy("(ii) Alias clustering method"),
                                     initial=mc.DEFAULT_ALIAS_METHOD, required=False)
    alias_threshold = forms.FloatField(
        label=gettext_lazy("(ii) Similarity threshold"), initial=mc.DEFAULT_ALIAS_THRESHOLD, required=False,
        min_value=mc.ALIAS_THRESHOLD_MIN, max_value=mc.ALIAS_THRESHOLD_MAX,
        widget=forms.NumberInput(attrs={"step": "0.01"}),
        help_text=gettext_lazy("Between 0.50 and 1.00. The thesis uses 0.85."),
    )
    # Rendered as a hidden input that the cascaded picker (Alpine.js) fills; validated against the catalog.
    classifier_id = forms.ChoiceField(label=gettext_lazy("(iii) Role classification model"),
                                      initial=mc.DEFAULT_CLASSIFIER_ID, required=False)

    RESEARCH_FIELDS = ("ner_model", "alias_method", "alias_threshold", "classifier_id")

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            # Research fields missing from the POST (simple mode) keep their defaults, so the panel still shows
            # the default models when the user switches to advanced mode after an analysis.
            data = data.copy()
            for name in self.RESEARCH_FIELDS:
                if not data.get(name):
                    data[name] = self.base_fields[name].initial
        super().__init__(data, *args, **kwargs)
        self.fields["text"].max_length = settings.ANALYSIS_MAX_CHARS
        best = _("best in the thesis")
        default = _("default")
        self.fields["ner_model"].choices = [
            (m.id, " · ".join([m.label, _("F1 CV %(f1)s") % {"f1": f1(m.f1_cv)},
                               _("macro F1 test %(f1)s") % {"f1": f1(m.f1_test)}]
                              + ([best, default] if m.id == mc.DEFAULT_NER_MODEL else [])))
            for m in mc.NER_MODELS.values()
        ]
        self.fields["alias_method"].choices = [
            (m.id, " · ".join([m.label, f"F1 {f1(m.f1)} (Tabel 4.37)"]
                              + ([best, default] if m.id == mc.DEFAULT_ALIAS_METHOD else [])))
            for m in mc.ALIAS_METHODS.values()
        ]
        # Every catalog id is a valid choice here; clean_classifier_id() rejects entries that are not available.
        self.fields["classifier_id"].choices = [(e.id, classifier_label(e)) for e in mc.CLASSIFIERS.values()]

    def clean_text(self):
        try:
            return validate_text(self.cleaned_data.get("text"))
        except TextValidationError as exc:
            raise forms.ValidationError(exc.user_message, code=exc.code) from exc

    def clean_classifier_id(self):
        value = self.cleaned_data.get("classifier_id") or mc.DEFAULT_CLASSIFIER_ID
        try:
            return mc.get_classifier_entry(value).id
        except UnknownModelError as exc:
            message = _("This model is not available yet. Choose another model.")
            raise forms.ValidationError(message, code="unavailable") from exc

    @property
    def mode_value(self) -> str:
        value = self["mode"].value()
        return "advanced" if value == "advanced" else "simple"

    @property
    def task_value(self) -> str:
        value = self["task"].value()
        return value if value in mc.TASKS else mc.DEFAULT_TASK

    @property
    def classifier_value(self) -> str:
        value = self["classifier_id"].value()
        return value if value in mc.CLASSIFIERS else mc.DEFAULT_CLASSIFIER_ID

    def config(self) -> mc.PipelineConfig:
        """General-user mode always uses the defaults; advanced mode (Mode Peneliti) uses the chosen models."""
        data = self.cleaned_data
        if data.get("mode") != "advanced":
            return mc.validate_config(task=data.get("task"))
        return mc.validate_config(
            task=data.get("task"), ner_model=data.get("ner_model"), alias_method=data.get("alias_method"),
            alias_threshold=data.get("alias_threshold"), classifier_id=data.get("classifier_id"),
        )
