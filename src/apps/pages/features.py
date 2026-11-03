"""Feature registry for the navbar dropdown, the landing page and /fitur/<slug>/.

Three features run in v1.0; the others are shown as "coming soon" only (no logic). Templates read this registry,
so the list of features is written once.
"""

from dataclasses import dataclass

from django.urls import reverse
from django.utils.translation import gettext_lazy as _


@dataclass(frozen=True)
class Feature:
    slug: str
    title: str
    summary: str
    icon: str
    available: bool
    task: str | None = None  # workspace task preselected by "Try it in the workspace" (?tugas=)

    @property
    def url(self) -> str:
        return reverse("pages:feature", args=[self.slug])

    @property
    def body_template(self) -> str:
        return f"pages/features/{self.slug}.html"


FEATURES = (
    Feature(
        "identifikasi-tokoh",
        _("Character identification"),
        _("Find character names in a satua and label each one with its entity type."),
        "search",
        True,
        "identify",
    ),
    Feature(
        "alias-clustering",
        _("Alias clustering"),
        _("Group the different names that refer to the same character."),
        "link",
        True,
        "alias",
    ),
    Feature(
        "klasifikasi-peran",
        _("Role classification"),
        _("Label each character group as protagonist or antagonist."),
        "scale",
        True,
        "role",
    ),
    Feature(
        "coreference",
        _("Coreference"),
        _("Link pronouns and other references back to the character they refer to."),
        "git-merge",
        False,
    ),
    Feature(
        "social-graph",
        _("Social graph"),
        _("Draw the network of characters that appear together in a story."),
        "share-2",
        False,
    ),
    Feature(
        "quote-attribution",
        _("Quote attribution"),
        _("Find direct speech in a satua and identify which character says it."),
        "quote",
        False,
    ),
    Feature(
        "summarization",
        _("Summarization"),
        _("Produce a short summary of a satua."),
        "align-left",
        False,
    ),
    Feature(
        "aksara-bali",
        _("Aksara Bali"),
        _("Transliterate Balinese script to Latin script so that texts in aksara Bali can be analysed too."),
        "type",
        False,
    ),
)

FEATURES_BY_SLUG = {feature.slug: feature for feature in FEATURES}
AVAILABLE_FEATURES = tuple(f for f in FEATURES if f.available)
COMING_SOON_FEATURES = tuple(f for f in FEATURES if not f.available)
