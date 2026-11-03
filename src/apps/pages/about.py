"""Content of the about page: team, publications and software (provided by the developer, 3 Nov 2026).

Names, academic titles and publication titles are proper nouns and are not translated. Only fill in a DOI or URL
that has been verified; leave it None otherwise and the page shows the entry without a link.
"""

from dataclasses import dataclass

from django.utils.translation import gettext_lazy as _

UNUD_INFORMATICS = _("Informatics Study Program, FMIPA, Universitas Udayana")


@dataclass(frozen=True)
class TeamMember:
    name: str
    role: str
    affiliation: str


@dataclass(frozen=True)
class Publication:
    title: str
    authors: str
    venue: str
    year: int
    url: str | None
    relevance: str


@dataclass(frozen=True)
class Software:
    name: str
    description: str
    url: str


TEAM = (
    TeamMember("I Made Satria Bimantara, S.Kom., M.Kom.", _("Team lead"), UNUD_INFORMATICS),
    TeamMember("Dr. Ir. Ngurah Agus Sanjaya ER, S.Kom., M.Kom.", _("Team member"), UNUD_INFORMATICS),
    TeamMember(
        "Prof. Dr. Ir. Diana Purwitasari, S.Kom., M.Sc.",
        _("Team member"),
        _("Department of Informatics Engineering, Institut Teknologi Sepuluh Nopember (ITS)"),
    ),
)

PUBLICATIONS = (
    Publication(
        "Character Entity Recognition Using Hybrid Binary-Particle Swarm Optimization and Conditional Random Field "
        "on Balinese Folklore Text",
        "I.M.S. Bimantara, N.A.S. Sanjaya ER, D. Purwitasari",
        "Springer, Lecture Notes in Computer Science vol. 14416 (iiWAS 2023)",
        2023,
        "https://doi.org/10.1007/978-3-031-48316-5_15",
        _("The core of the character identification module (BPSO-CRF, five entity labels)."),
    ),
    Publication(
        "Balinese Story Texts Dataset for Narrative Text Analyses",
        "I.M.S. Bimantara, D. Purwitasari, N.A.S. Sanjaya ER, P.G.S. Natha",
        "Data in Brief vol. 56, 110781 (Elsevier)",
        2024,
        "https://doi.org/10.1016/j.dib.2024.110781",
        _("The Balinese satua text dataset for narrative analysis that PrasiBali.ai builds on."),
    ),
)

SOFTWARE = (
    Software(
        "balinese-nlp 2.4.2",
        _("Python package on PyPI with the character identification and alias clustering models."),
        "https://pypi.org/project/balinese-nlp/2.4.2/",
    ),
    Software(
        "BaliStoryAnalyzer",
        _("GitHub repository of the earlier research software for Balinese story analysis."),
        "https://github.com/satriabimantara/balinese_storyanalyzer",
    ),
)
