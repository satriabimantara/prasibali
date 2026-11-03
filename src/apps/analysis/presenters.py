"""Turn an AnalysisResult (fresh or from the history) into template data.

Highlights are built from text segments and mention offsets and rendered with Django autoescaping (DESIGN.md
"Keamanan rendering"): user text is never marked safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django.utils.formats import number_format
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from .services import model_catalog as mc
from .services.exceptions import UnknownModelError
from .services.pipeline import AnalysisResult, CharacterGroup, EntityMention, RoleResult

ENTITY_LABELS = ("PNAME", "ANM", "GODS", "ADJ", "OBJ")


def f1(value) -> str:
    return "–" if value is None else number_format(value, 4)


@dataclass
class Segment:
    text: str
    mention: EntityMention | None = None
    key: str = ""  # character key: the alias group id, or "n<index>" for an ungrouped name
    role_key: str = "none"
    group_number: int | None = None

    @property
    def label_class(self) -> str:
        label = self.mention.label if self.mention else ""
        return label.lower() if label in ENTITY_LABELS else "other"


@dataclass
class CharacterContext:
    """Sentences that mention one character (group), shown when its highlight is selected."""

    key: str
    title: str
    aliases: list[str]
    labels: list[str]
    role: RoleResult | None
    color_index: int | None
    sentences: list[list[Segment]] = field(default_factory=list)


@dataclass
class GroupView:
    group: CharacterGroup
    role: RoleResult | None
    labels: list[str]
    score: dict | None


def mention_key(mention: EntityMention, name_keys: dict[str, str]) -> str:
    return mention.group_id or name_keys.get(mention.text, "")


def _name_keys(result: AnalysisResult) -> dict[str, str]:
    """Keys for names that belong to no group (task "identify only", or a name the clustering left out)."""
    names = sorted({m.text for m in result.mentions if not m.group_id})
    return {name: f"n{i}" for i, name in enumerate(names, start=1)}


def build_segments(result: AnalysisResult, name_keys: dict[str, str] | None = None) -> list[Segment]:
    name_keys = name_keys if name_keys is not None else _name_keys(result)
    numbers = {g.group_id: g.number for g in result.groups}
    roles = result.roles_by_group
    segments: list[Segment] = []
    cursor = 0
    text = result.display_text
    for mention in sorted(result.mentions, key=lambda m: (m.start, -m.end)):
        if mention.start < cursor or mention.end > len(text):
            continue  # overlapping or out of range: keep the text plain
        if mention.start > cursor:
            segments.append(Segment(text[cursor:mention.start]))
        role = roles.get(mention.group_id)
        segments.append(Segment(text[mention.start:mention.end], mention, mention_key(mention, name_keys),
                                role.role_key if role else "none", numbers.get(mention.group_id)))
        cursor = mention.end
    if cursor < len(text):
        segments.append(Segment(text[cursor:]))
    return segments


def _sentence_offsets(result: AnalysisResult) -> list[int]:
    """Start offset of every sentence in display_text (sentences are joined with one space)."""
    offsets, position = [], 0
    for sentence in result.sentences:
        offsets.append(position)
        position += len(sentence) + 1
    return offsets


def _sentence_segments(sentence: str, start: int, mentions: list[EntityMention], key: str,
                       name_keys: dict[str, str]) -> list[Segment]:
    """One sentence split into plain text and the selected character's mentions."""
    segments, cursor = [], 0
    for mention in sorted(mentions, key=lambda m: m.start):
        if mention_key(mention, name_keys) != key:
            continue
        begin, end = mention.start - start, mention.end - start
        if begin < cursor or end > len(sentence):
            continue
        if begin > cursor:
            segments.append(Segment(sentence[cursor:begin]))
        segments.append(Segment(sentence[begin:end], mention, key))
        cursor = end
    if cursor < len(sentence):
        segments.append(Segment(sentence[cursor:]))
    return segments


def build_contexts(result: AnalysisResult, name_keys: dict[str, str]) -> list[CharacterContext]:
    roles = result.roles_by_group
    offsets = _sentence_offsets(result)
    by_sentence: dict[int, list[EntityMention]] = {}
    by_key: dict[str, list[EntityMention]] = {}
    for mention in result.mentions:
        by_sentence.setdefault(mention.sentence_index, []).append(mention)
        key = mention_key(mention, name_keys)
        if key:
            by_key.setdefault(key, []).append(mention)

    def labels_of(mentions):
        return sorted({m.label for m in mentions})

    contexts = []
    groups = {g.group_id: g for g in result.groups}
    titles = {g.group_id: (g.aliases[0] if g.aliases else g.group_id, g.aliases, g.color_index)
              for g in result.groups}
    titles.update({key: (name, [name], None) for name, key in name_keys.items()})
    for key, mentions in by_key.items():
        title, aliases, color = titles.get(key, (mentions[0].text, [mentions[0].text], None))
        context = CharacterContext(key, title, list(aliases), labels_of(mentions), roles.get(key), color)
        for index in sorted({m.sentence_index for m in mentions}):
            if 0 <= index < len(result.sentences):
                context.sentences.append(_sentence_segments(
                    result.sentences[index], offsets[index], by_sentence[index], key, name_keys))
        contexts.append(context)
    order = {g.group_id: g.number for g in groups.values()}
    contexts.sort(key=lambda c: (order.get(c.key, len(order) + 1), c.title))
    return contexts


# --------------------------------------------------------------------------- model score
PROBABILITY_NOTES = {
    # All KNN pickles: n_neighbors=9, weights="distance" (checked 3 Nov 2026).
    "knn": gettext_lazy(
        "For KNN it is the distance-weighted share of the 9 nearest training examples with this label."
    ),
    "rf": gettext_lazy("For Random Forest it is the average vote of the trees."),
    "dt": gettext_lazy("For a Decision Tree it is the share of training examples with this label in the leaf."),
    "gnb": gettext_lazy("For Gaussian Naive Bayes it is the posterior probability of the model."),
    "mlp": gettext_lazy("For the Multilayer Perceptron it is the output of the network's final layer."),
}


def score_view(role: RoleResult | None, algorithm_code: str | None) -> dict | None:
    """The raw model score with an explanation of what it is. Never presented as confidence or a percentage."""
    if role is None:
        return None
    if role.decision_score is not None:
        return {
            "kind": "decision",
            "name": _("SVM decision_function"),
            "value": number_format(role.decision_score, 4),
            "explanation": _(
                "Signed distance to the separating hyperplane, not a probability. The sign shows the side: "
                "positive for Protagonist, negative for Antagonist. Values near 0 lie close to the boundary."
            ),
        }
    if role.probability is not None:
        return {
            "kind": "probability",
            "name": _("Estimated probability (predict_proba)"),
            "value": number_format(role.probability, 2),
            "explanation": " ".join([
                _("The model's estimate, between 0 and 1, for the chosen label."),
                str(PROBABILITY_NOTES.get(algorithm_code or "", "")),
            ]).strip(),
        }
    return None


# --------------------------------------------------------------------------- configuration panel
def _classifier_or_none(catalog_id: str | None) -> mc.ClassifierEntry | None:
    try:
        return mc.get_classifier_entry(catalog_id, require_available=False) if catalog_id else None
    except UnknownModelError:
        return None


def present_config(config: dict, model_version: dict, timings: dict | None = None,
                   duration_ms: int | None = None) -> dict:
    """Configuration and model version of a run, for the "Models used" panel and the history detail."""
    task = config.get("task", mc.DEFAULT_TASK)
    runs_alias = task in mc.ALIAS_TASKS
    runs_roles = task in mc.ROLE_TASKS
    alias_method = mc.ALIAS_METHODS.get(config.get("alias_method", ""))
    classifier_info = model_version.get("classifier") or {}
    entry = _classifier_or_none(classifier_info.get("id") or (config.get("classifier_id") if runs_roles else None))
    return {
        "mode": config.get("mode", "simple"),
        "task": task,
        "task_label": mc.TASKS.get(task, task),
        "ner": mc.NER_MODELS.get(config.get("ner_model", "")),
        "runs_alias": runs_alias,
        "alias": alias_method,
        "alias_threshold": config.get("alias_threshold"),
        "runs_roles": runs_roles,
        "classifier": entry,
        "classifier_variant": mc.VARIANTS.get(entry.variant) if entry else None,
        "classifier_feature_type": mc.FEATURE_TYPES.get(entry.feature_type) if entry else None,
        "classifier_file": classifier_info,
        "embedding": classifier_info.get("embedding"),
        "versions": {k: model_version.get(k) for k in ("balinese_nlp", "scikit_learn")},
        "timings": timings or {},
        "duration_ms": duration_ms,
    }


# --------------------------------------------------------------------------- result
def present(result: AnalysisResult, *, duration_ms: int | None = None) -> dict:
    roles = result.roles_by_group
    config = result.config
    has_roles = bool(result.roles)
    name_keys = _name_keys(result)
    entry = _classifier_or_none(config.get("classifier_id")) if has_roles else None
    algorithm_code = entry.algorithm_code if entry else None
    labels_by_group: dict[str, set[str]] = {}
    for mention in result.mentions:
        if mention.group_id:
            labels_by_group.setdefault(mention.group_id, set()).add(mention.label)
    groups = [
        GroupView(group, roles.get(group.group_id), sorted(labels_by_group.get(group.group_id, ())),
                  score_view(roles.get(group.group_id), algorithm_code))
        for group in result.groups
    ]
    return {
        "result": result,
        "segments": build_segments(result, name_keys),
        "contexts": build_contexts(result, name_keys),
        "groups": groups,
        "ungrouped_characters": result.characters if not result.groups else [],
        "count_groups": len(result.groups) if result.groups else len(result.characters),
        "count_protagonis": sum(1 for r in result.roles if r.role_key == "protagonis"),
        "count_antagonis": sum(1 for r in result.roles if r.role_key == "antagonis"),
        "has_roles": has_roles,
        "classifier": entry,
        "labels_used": sorted({m.label for m in result.mentions if m.label in ENTITY_LABELS},
                              key=ENTITY_LABELS.index),
        "config_view": present_config(config, result.model_version, result.timings, duration_ms),
        "total_seconds": round(sum(result.timings.values()), 1),
    }
