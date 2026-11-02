"""Turn an AnalysisResult into template data. Highlights are built from text segments and mention offsets and
rendered with Django autoescaping (DESIGN.md "Keamanan rendering"): user text is never marked safe."""

from __future__ import annotations

from dataclasses import dataclass

from .services.model_catalog import NER_MODELS, get_classifier_entry
from .services.pipeline import AnalysisResult, CharacterGroup, EntityMention, RoleResult


@dataclass
class Segment:
    text: str
    mention: EntityMention | None = None
    role_key: str = "none"
    group_number: int | None = None


@dataclass
class GroupView:
    group: CharacterGroup
    role: RoleResult | None


def build_segments(result: AnalysisResult) -> list[Segment]:
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
        segments.append(Segment(text[mention.start:mention.end], mention,
                                role.role_key if role else "none", numbers.get(mention.group_id)))
        cursor = mention.end
    if cursor < len(text):
        segments.append(Segment(text[cursor:]))
    return segments


def present(result: AnalysisResult) -> dict:
    roles = result.roles_by_group
    config = result.config
    has_roles = bool(result.roles)
    return {
        "result": result,
        "segments": build_segments(result),
        "groups": [GroupView(group, roles.get(group.group_id)) for group in result.groups],
        "ungrouped_characters": result.characters if not result.groups else [],
        "count_groups": len(result.groups) if result.groups else len(result.characters),
        "count_protagonis": sum(1 for r in result.roles if r.role_key == "protagonis"),
        "count_antagonis": sum(1 for r in result.roles if r.role_key == "antagonis"),
        "has_roles": has_roles,
        "classifier": get_classifier_entry(config["classifier_id"]) if has_roles else None,
        "ner_model": NER_MODELS[config["ner_model"]],
        "has_scores": any(r.decision_score is not None for r in result.roles),
        "total_seconds": round(sum(result.timings.values()), 1),
    }
