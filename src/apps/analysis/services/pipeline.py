"""PrasiBali.ai analysis pipeline: (i) character identification, (ii) alias clustering, (iii) role classification.

Follows scripts/test_pretrained_pipeline.py step by step (the flow verified against the real models). The only
structural difference: task (i) keeps entity labels and positions by rebuilding names from predict_sentence() with
exactly the rules of BaseModel.extract_predicted_characters_from_sentence, so the set of characters equals
BaseModel.identify_characters() while running the NER model once per sentence.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from importlib import metadata

from django.conf import settings
from django.utils.translation import gettext as _

from . import embeddings
from .exceptions import (
    AliasClusteringError,
    AnalysisError,
    CharacterIdentificationError,
    PreprocessingError,
    RoleClassificationError,
)
from .features import check_feature_count, featurize, score_and_probability
from .model_catalog import ALIAS_METHODS, PipelineConfig, get_classifier_entry, validate_config
from .model_registry import PREDICT_LOCK, get_classifier, get_label_encoder, get_ner_model
from .preprocessing import PreprocessedStory, preprocess_context, preprocess_story
from .sentence_grouping import group_sentences

logger = logging.getLogger(__name__)

ROLE_KEYS = {"Protagonis": "protagonis", "Antagonis": "antagonis"}
GROUP_PALETTE_SIZE = 6  # group-1..group-6 tokens in DESIGN.md


@dataclass
class EntityMention:
    text: str  # character name as identified (tokens joined with a space)
    label: str  # entity type: PNAME, ANM, GODS, ADJ or OBJ
    sentence_index: int
    start: int  # offsets into AnalysisResult.display_text
    end: int
    group_id: str | None = None


@dataclass
class CharacterGroup:
    group_id: str  # key from alias clustering, e.g. "Tokoh-1"
    number: int  # 1-based position, shown in Mode Peneliti
    aliases: list[str]
    mention_count: int
    color_index: int  # 1..GROUP_PALETTE_SIZE


@dataclass
class RoleResult:
    group_id: str
    role: str  # label from the encoder: "Protagonis" or "Antagonis"
    role_key: str  # "protagonis" | "antagonis", for styling
    decision_score: float | None  # SVM: signed distance to the hyperplane, not a probability
    probability: float | None  # kept for later versions; v1.0 does not display it
    context_words: int
    known_terms: int | None  # TF-IDF terms known to the vectorizer (TF4 only)
    low_context: bool


@dataclass
class AnalysisResult:
    config: dict
    display_text: str
    sentences: list[str]
    characters: list[str]
    mentions: list[EntityMention]
    groups: list[CharacterGroup]
    roles: list[RoleResult]
    timings: dict[str, float]
    model_version: dict
    warnings: list[str] = field(default_factory=list)

    @property
    def roles_by_group(self) -> dict[str, RoleResult]:
        return {role.group_id: role for role in self.roles}

    def as_dict(self) -> dict:
        """JSON-serialisable form (stored with each analysis run from Sesi 4 on)."""
        return asdict(self)


# --------------------------------------------------------------------------- task (i)
def _names_from_tags(tokens: list[str], tags) -> list[dict]:
    """Same rules as BaseModel.extract_predicted_characters_from_sentence, keeping token indices and labels.

    B-* starts a name; I-* extends the current name (or starts one if none yet, even after O); O is skipped.
    """
    names: list[dict] = []
    for index, word in enumerate(tokens):
        tag = str(tags[index])
        prefix, _sep, label = tag.partition("-")
        if prefix == "B" or (prefix == "I" and not names):
            names.append({"text": word, "first": index, "last": index, "label": label})
        elif prefix == "I":
            names[-1]["text"] = f"{names[-1]['text']} {word}"
            names[-1]["last"] = index
    return names


def identify_characters(story: PreprocessedStory, ner_model: str) -> tuple[list[str], list[EntityMention]]:
    """Characters (sorted, unique) and every mention with its entity label and position in display_text."""
    model = get_ner_model(ner_model)
    characters: set[str] = set()
    mentions: list[EntityMention] = []
    sentence_start = 0
    for sentence_index, sentence in enumerate(story.sentences):
        tags, _tagged = model.predict_sentence(sentence)
        tokens = sentence.split(" ")
        names = _names_from_tags(tokens, tags)
        # BaseModel.identify_characters joins names with '; ', splits on ';' and strips each part.
        if names:
            characters.update(part.strip() for part in "; ".join(n["text"] for n in names).split(";"))
        offsets, position = [], 0
        for token in tokens:
            offsets.append(position)
            position += len(token) + 1
        for name in names:
            text = name["text"].strip()
            if not text:
                continue
            start = offsets[name["first"]]
            end = offsets[name["last"]] + len(tokens[name["last"]])
            mentions.append(EntityMention(text, name["label"] or "?", sentence_index,
                                          sentence_start + start, sentence_start + end))
        sentence_start += len(sentence) + 1  # display_text joins sentences with one space
    return sorted(characters), mentions


# --------------------------------------------------------------------------- task (ii)
def cluster_aliases(characters: list[str], method: str, threshold: float) -> dict[str, list[str]]:
    if method not in ALIAS_METHODS:
        raise AliasClusteringError(detail=f"Unknown alias method {method!r}")
    from balinese_nlp.narratives.aliasclustering.rule_based import AliasClusteringRuleBased

    clusterer = AliasClusteringRuleBased(pairwise_distance=method, avg_threshold_similarity=threshold)
    clusterer.fit(list(characters))
    # fit() deduplicates through a set, whose order changes with Python's per-process hash seed, and the greedy
    # clustering depends on that order. Sorting makes the same text give the same groups on every run.
    clusterer.pred_characters = sorted(clusterer.pred_characters)
    return {str(key): list(aliases) for key, aliases in clusterer.cluster().items()}


def build_groups(groups: dict[str, list[str]], mentions: list[EntityMention]) -> list[CharacterGroup]:
    """Assign each mention to the group whose aliases contain its exact text, and count mentions per group."""
    group_of = {}
    for key, aliases in groups.items():
        for alias in aliases:
            group_of.setdefault(alias, key)
    counts = dict.fromkeys(groups, 0)
    for mention in mentions:
        mention.group_id = group_of.get(mention.text)
        if mention.group_id is not None:
            counts[mention.group_id] += 1
    return [
        CharacterGroup(key, number, list(aliases), counts[key], (number - 1) % GROUP_PALETTE_SIZE + 1)
        for number, (key, aliases) in enumerate(groups.items(), start=1)
    ]


# --------------------------------------------------------------------------- task (iii)
def classify_roles(story: PreprocessedStory, groups: dict[str, list[str]], catalog_id: str):
    """Role per character group. Returns (roles, classifier info for model_version)."""
    classifier = get_classifier(catalog_id)
    encoder = get_label_encoder()
    frame = group_sentences(story.sentences, groups)
    if "GroupedSentences" not in frame.columns:
        raise RoleClassificationError(detail=f"No GroupedSentences column: {list(frame.columns)}")
    contexts = [preprocess_context(value) for value in frame["GroupedSentences"]]
    group_ids = [str(v) for v in frame["CharactersID"]] if "CharactersID" in frame.columns else list(groups)
    with PREDICT_LOCK:
        features, known_terms, _feature_timings = featurize(
            classifier.extractors, contexts, embedding_loader=embeddings.load_fasttext, scaler=classifier.scaler,
        )
        check_feature_count(classifier.estimator, features)
        labels = encoder.encoder.inverse_transform(classifier.estimator.predict(features))
        scores, probabilities = score_and_probability(classifier.estimator, features)
    known_terms = known_terms or [None] * len(contexts)
    threshold = settings.ANALYSIS_LOW_CONTEXT_WORDS
    roles = []
    for i, group_id in enumerate(group_ids):
        words = len(contexts[i].split())
        roles.append(RoleResult(
            group_id=group_id,
            role=str(labels[i]),
            role_key=ROLE_KEYS.get(str(labels[i]), "none"),
            decision_score=scores[i],
            probability=probabilities[i],
            context_words=words,
            known_terms=known_terms[i],
            low_context=words < threshold or known_terms[i] == 0,
        ))
    info = {
        "id": classifier.entry.id,
        "file": classifier.filename,
        "sha256": classifier.sha256,
        "label_encoder_sha256": encoder.sha256,
        "classes": [str(c) for c in encoder.encoder.classes_],
    }
    if classifier.entry.uses_tf5:
        info["embedding"] = embeddings.embedding_identity(embeddings.load_fasttext())
    return roles, info


# --------------------------------------------------------------------------- full run
def _package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def run_full_pipeline(raw_text: str, config: PipelineConfig | None = None) -> AnalysisResult:
    """Validate and preprocess, then run the stages the task needs. Raises an AnalysisError subclass per stage."""
    config = config or validate_config()
    get_classifier_entry(config.classifier_id)  # whitelist check before any work
    timings: dict[str, float] = {}

    def timed(name, error_cls, func):
        started = time.perf_counter()
        try:
            return func()
        except AnalysisError as exc:
            logger.warning("Analysis stage %s failed: %s", name, exc.detail or exc)
            raise
        except Exception as exc:
            logger.exception("Analysis stage %s failed", name)
            raise error_cls(detail=repr(exc)) from exc
        finally:
            timings[name] = round(time.perf_counter() - started, 3)

    story = timed("preprocess", PreprocessingError, lambda: preprocess_story(raw_text))
    warnings = list(story.warnings)
    characters, mentions = timed("identify", CharacterIdentificationError,
                                 lambda: identify_characters(story, config.ner_model))
    model_version = {
        "balinese_nlp": _package_version("balinese-nlp"),
        "scikit_learn": _package_version("scikit-learn"),
        "ner_model": config.ner_model,
    }
    groups: dict[str, list[str]] = {}
    group_list: list[CharacterGroup] = []
    roles: list[RoleResult] = []
    if not characters:
        warnings.append(_("No characters were recognised. Check that the text is written in Balinese."))
    elif config.runs_alias:
        groups = timed("alias", AliasClusteringError,
                       lambda: cluster_aliases(characters, config.alias_method, config.alias_threshold))
        group_list = build_groups(groups, mentions)
        model_version["alias"] = {"method": config.alias_method, "threshold": config.alias_threshold}
        if config.runs_roles and groups:
            roles, classifier_info = timed("role", RoleClassificationError,
                                           lambda: classify_roles(story, groups, config.classifier_id))
            model_version["classifier"] = classifier_info
    return AnalysisResult(
        config=config.as_dict(),
        display_text=story.display_text,
        sentences=story.sentences,
        characters=characters,
        mentions=mentions,
        groups=group_list,
        roles=roles,
        timings=timings,
        model_version=model_version,
        warnings=warnings,
    )
