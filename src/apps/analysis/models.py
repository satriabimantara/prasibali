"""One row per analysis request: input, configuration, output and model version (the analysis history and log)."""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .services.model_catalog import TASKS


class AnalysisRun(models.Model):
    class Status(models.TextChoices):
        PROCESSING = "processing", _("Processing")
        SUCCESS = "success", _("Finished")
        FAILED = "failed", _("Failed")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="analysis_runs", verbose_name=_("user")
    )
    task_type = models.CharField(_("task"), max_length=20, choices=list(TASKS.items()))
    input_text = models.TextField(_("satua text"))
    # PipelineConfig.as_dict() plus the display mode ("simple" or "advanced").
    config = models.JSONField(_("configuration"), default=dict, blank=True)
    # AnalysisResult.as_dict() when the run succeeded.
    output = models.JSONField(_("output"), null=True, blank=True)
    status = models.CharField(_("status"), max_length=20, choices=Status.choices, default=Status.PROCESSING)
    error_stage = models.CharField(_("failed stage"), max_length=20, blank=True)
    error_message = models.TextField(_("error message"), blank=True)  # user-facing message
    error_detail = models.TextField(_("technical detail"), blank=True)  # for the admin log only
    duration_ms = models.PositiveIntegerField(_("duration (ms)"), null=True, blank=True)
    # balinese-nlp and scikit-learn versions, NER model, alias settings, classifier id + pickle hash, embedding.
    model_version = models.JSONField(_("model version"), default=dict, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("user", "-created_at"), name="analysis_user_created_idx")]
        verbose_name = _("analysis run")
        verbose_name_plural = _("analysis runs")

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def title(self) -> str:
        """First words of the satua, used as its name in the history."""
        first_line = next((line.strip() for line in self.input_text.splitlines() if line.strip()), "")
        return first_line if len(first_line) <= 60 else first_line[:57].rstrip() + "..."

    @property
    def classifier_id(self) -> str | None:
        return (self.model_version.get("classifier") or {}).get("id") or None

    @property
    def mode(self) -> str:
        return "advanced" if self.config.get("mode") == "advanced" else "simple"


class DailyUsage(models.Model):
    """Analyses counted against the daily quota, per user and local day (TIME_ZONE).

    Kept apart from AnalysisRun so that deleting the history does not give the quota back.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_usage", verbose_name=_("user")
    )
    day = models.DateField(_("day"))
    used = models.PositiveIntegerField(_("analyses used"), default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("user", "day"), name="analysis_daily_usage_unique")]
        ordering = ("-day",)
        verbose_name = _("daily usage")
        verbose_name_plural = _("daily usage")

    def __str__(self):
        return f"{self.user} {self.day}: {self.used}"
