"""Exceptions raised by the analysis services, one family per pipeline stage.

Every `AnalysisError` carries a `user_message` (translated, safe to show) and an optional technical `detail` for
logs. Views show `user_message` only; the detail never reaches the page.
"""

from django.utils.translation import gettext_lazy as _


class AnalysisError(Exception):
    stage = "analysis"
    default_message = _("The analysis could not be completed. Your text has not been lost.")

    def __init__(self, user_message=None, detail: str = ""):
        self.user_message = user_message or self.default_message
        self.detail = detail
        super().__init__(detail or str(self.user_message))


class TextValidationError(AnalysisError):
    """The submitted satua cannot be analysed (empty, too long, no sentences, Balinese script)."""

    stage = "validation"

    def __init__(self, code: str, user_message, detail: str = ""):
        self.code = code
        super().__init__(user_message, detail)


class PreprocessingError(AnalysisError):
    stage = "preprocessing"
    default_message = _("The text could not be prepared for analysis. Check that it is a Balinese story.")


class CharacterIdentificationError(AnalysisError):
    stage = "identify"
    default_message = _(
        "Character identification failed because the model did not respond. Your text has not been lost."
    )


class AliasClusteringError(AnalysisError):
    stage = "alias"
    default_message = _("Grouping the characters' other names failed. Your text has not been lost.")


class RoleClassificationError(AnalysisError):
    stage = "role"
    default_message = _("Role classification failed because the model did not respond. Your text has not been lost.")


class ModelsUnavailableError(RoleClassificationError):
    """The pretrained-models folder or a pickle is missing or unreadable. Identification and grouping still work."""

    default_message = _(
        "The role classification model is not available right now. Character identification and grouping still work."
    )


class EmbeddingError(RoleClassificationError):
    """The FastText word embedding for feature TF5 is missing or does not match the classifier."""

    default_message = _(
        "The word embedding needed by this model is not available right now. Try another model or try again later."
    )


class UnknownModelError(ValueError):
    """A model id that is not in the catalog whitelist. Never shown verbatim to users."""
