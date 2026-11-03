"""Daily quota and the lifecycle of an AnalysisRun: start (quota check + row), execute (pipeline), record outcome."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext as _

from .models import AnalysisRun, DailyUsage
from .services.exceptions import AnalysisError, TextValidationError
from .services.model_catalog import PipelineConfig
from .services.pipeline import AnalysisResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QuotaStatus:
    limit: int  # 0 = unlimited
    used: int

    @property
    def unlimited(self) -> bool:
        return self.limit <= 0

    @property
    def remaining(self) -> int | None:
        return None if self.unlimited else max(self.limit - self.used, 0)

    @property
    def exhausted(self) -> bool:
        return not self.unlimited and self.used >= self.limit


class QuotaExceeded(Exception):
    def __init__(self, quota: QuotaStatus):
        self.quota = quota
        super().__init__(f"Daily quota of {quota.limit} analyses used")


def local_today(now=None) -> date:
    """Today in TIME_ZONE (Asia/Makassar): the quota resets at local midnight."""
    return timezone.localdate(now or timezone.now())


def quota_status(user, now=None) -> QuotaStatus:
    usage = DailyUsage.objects.filter(user=user, day=local_today(now)).values_list("used", flat=True).first()
    return QuotaStatus(limit=settings.ANALYSIS_DAILY_QUOTA, used=usage or 0)


def start_run(user, text: str, config: PipelineConfig, mode: str) -> AnalysisRun:
    """Check and use one unit of today's quota, and create the run, in one transaction. Raises QuotaExceeded."""
    with transaction.atomic():
        # Lock the user's row so two simultaneous requests cannot both pass the quota check (PostgreSQL).
        get_user_model().objects.select_for_update().filter(pk=user.pk).first()
        quota = quota_status(user)
        if quota.exhausted:
            raise QuotaExceeded(quota)
        usage, _created = DailyUsage.objects.get_or_create(user=user, day=local_today())
        DailyUsage.objects.filter(pk=usage.pk).update(used=F("used") + 1)
        return AnalysisRun.objects.create(
            user=user,
            task_type=config.task,
            input_text=text,
            config={**config.as_dict(), "mode": "advanced" if mode == "advanced" else "simple"},
            status=AnalysisRun.Status.PROCESSING,
        )


def refund_quota(run: AnalysisRun) -> None:
    """Failed runs do not count: give back the unit used by start_run()."""
    DailyUsage.objects.filter(user_id=run.user_id, day=local_today(run.created_at), used__gt=0).update(
        used=F("used") - 1
    )


def execute_run(
    run: AnalysisRun, config: PipelineConfig, pipeline: Callable[[str, PipelineConfig], AnalysisResult]
) -> AnalysisResult | None:
    """Run the pipeline and store the outcome on `run`. Returns the result, or None when the run failed.

    TextValidationError propagates (after deleting the run): it is a problem with the input, shown on the form.
    """
    started = time.perf_counter()
    result = None
    try:
        result = pipeline(run.input_text, config)
    except TextValidationError:
        refund_quota(run)
        run.delete()
        raise
    except AnalysisError as exc:
        run.status = AnalysisRun.Status.FAILED
        run.error_stage = exc.stage
        run.error_message = str(exc.user_message)
        run.error_detail = (exc.detail or "")[:4000]
    except Exception as exc:  # any other failure must still be recorded and shown kindly (logged with traceback)
        logger.exception("Analysis run %s failed unexpectedly", run.pk)
        run.status = AnalysisRun.Status.FAILED
        run.error_stage = "analysis"
        run.error_message = str(AnalysisError.default_message)
        run.error_detail = repr(exc)[:4000]
    else:
        run.status = AnalysisRun.Status.SUCCESS
        run.output = result.as_dict()
        run.model_version = result.model_version
    run.duration_ms = round((time.perf_counter() - started) * 1000)
    run.save()
    if run.status == AnalysisRun.Status.FAILED:
        refund_quota(run)
    return result


def quota_message(quota: QuotaStatus) -> str:
    return _("You have used today's quota of %(limit)s analyses. The quota resets at midnight (WITA).") % {
        "limit": quota.limit
    }
