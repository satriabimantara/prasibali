"""Analysis form. Every model choice comes from the catalog (services/model_catalog.py), never from templates."""

from django import forms
from django.conf import settings
from django.utils.formats import number_format
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from .services import model_catalog as mc
from .services.exceptions import TextValidationError, UnknownModelError
from .services.preprocessing import validate_text

MODES = (("simple", gettext_lazy("Simple")), ("advanced", gettext_lazy("Advanced")))


def f1(value) -> str:
    return "–" if value is None else number_format(value, 4)


class SelectWithDisabled(forms.Select):
    """Select that renders some options disabled (catalog entries that are not available yet)."""

    def __init__(self, *args, disabled_values=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.disabled_values = set(disabled_values)

    def create_option(self, name, value, *args, **kwargs):
        option = super().create_option(name, value, *args, **kwargs)
        if value in self.disabled_values:
            option["attrs"]["disabled"] = True
        return option


def classifier_label(entry: mc.ClassifierEntry) -> str:
    parts = [f"{entry.algorithm_label} · {entry.feature_label}",
             _("CV F1 %(f1)s (%(ref)s)") % {"f1": f1(entry.f1_cv), "ref": entry.thesis_ref_cv}]
    if entry.f1_test is not None:
        parts.append(_("test F1 %(f1)s (%(ref)s)") % {"f1": f1(entry.f1_test), "ref": entry.thesis_ref_test})
    else:
        parts.append(_("test F1 –"))
    if entry.is_default:
        parts.append(_("best in the thesis"))
    if not entry.available:
        parts.append(_("coming soon"))
    return " · ".join(parts)


def classifier_choices():
    titles = {
        "m2-wordvector": _("M2 · Word vector"),
        "m1-wordvector": _("M1 · Word vector"),
        "m2-lexicon": _("M2 · Lexicon (coming soon)"),
        "m1-lexicon": _("M1 · Lexicon (coming soon)"),
    }
    return [(titles[key], [(e.id, classifier_label(e)) for e in entries]) for key, entries in mc.classifier_groups()]


class AnalysisForm(forms.Form):
    text = forms.CharField(
        label=gettext_lazy("Satua text"),
        required=False,  # validate_text() gives the specific message
        widget=forms.Textarea(attrs={"rows": 12, "lang": "ban", "spellcheck": "false"}),
        help_text=gettext_lazy("Balinese text in Latin script. End every sentence with a full stop."),
    )
    mode = forms.ChoiceField(choices=MODES, initial="simple", required=False, widget=forms.HiddenInput)
    task = forms.ChoiceField(label=gettext_lazy("What to analyse"), choices=list(mc.TASKS.items()),
                             initial=mc.DEFAULT_TASK)
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
    classifier_id = forms.ChoiceField(label=gettext_lazy("(iii) Role classification model"),
                                      initial=mc.DEFAULT_CLASSIFIER_ID, required=False)

    RESEARCH_FIELDS = ("ner_model", "alias_method", "alias_threshold", "classifier_id")

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            # Research fields missing from the POST (simple mode) keep their defaults, so the panel still shows
            # the best models when the user switches to advanced mode after an analysis.
            data = data.copy()
            for name in self.RESEARCH_FIELDS:
                if not data.get(name):
                    data[name] = self.base_fields[name].initial
        super().__init__(data, *args, **kwargs)
        self.fields["text"].max_length = settings.ANALYSIS_MAX_CHARS
        self.fields["ner_model"].choices = [
            (m.id, " · ".join([m.label, _("CV F1 %(f1)s") % {"f1": f1(m.f1_cv)},
                               _("test F1 %(f1)s") % {"f1": f1(m.f1_test)}]
                              + ([_("best in the thesis")] if m.id == mc.DEFAULT_NER_MODEL else [])))
            for m in mc.NER_MODELS.values()
        ]
        self.fields["alias_method"].choices = [
            (m.id, " · ".join([m.label, f"F1 {f1(m.f1)} (Tabel 4.37)"]
                              + ([_("best in the thesis")] if m.id == mc.DEFAULT_ALIAS_METHOD else [])))
            for m in mc.ALIAS_METHODS.values()
        ]
        field = self.fields["classifier_id"]
        field.choices = classifier_choices()
        field.widget = SelectWithDisabled(
            choices=field.choices, disabled_values=[e.id for e in mc.CLASSIFIERS.values() if not e.available])

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

    def config(self) -> mc.PipelineConfig:
        """Simple mode always uses the defaults (best models in the thesis); advanced mode uses the chosen ones."""
        data = self.cleaned_data
        if data.get("mode") != "advanced":
            return mc.validate_config(task=data.get("task"))
        return mc.validate_config(
            task=data.get("task"), ner_model=data.get("ner_model"), alias_method=data.get("alias_method"),
            alias_threshold=data.get("alias_threshold"), classifier_id=data.get("classifier_id"),
        )
