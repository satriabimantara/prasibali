"""Admin for the analysis log: read-only view of every run (input, configuration, output, errors, timing)."""

import json

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import AnalysisRun, DailyUsage


@admin.register(AnalysisRun)
class AnalysisRunAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "task_type", "mode_display", "classifier_display", "status",
                    "error_stage", "duration_ms")
    list_filter = ("status", "task_type", "error_stage", "created_at")
    search_fields = ("id", "user__email", "error_message", "error_detail")
    date_hierarchy = "created_at"
    list_select_related = ("user",)
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("id", "user", "created_at", "task_type", "status", "duration_ms")}),
        (_("Error"), {"fields": ("error_stage", "error_message", "error_detail")}),
        (_("Configuration and model version"), {"fields": ("config_pretty", "model_version_pretty")}),
        (_("Input"), {"fields": ("input_text",)}),
        (_("Output"), {"classes": ("collapse",), "fields": ("output_pretty",)}),
    )

    # The log is read-only: runs are created by the analysis view only.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [f for fs in self.fieldsets for f in fs[1]["fields"]]

    @admin.display(description=_("mode"))
    def mode_display(self, obj):
        return obj.mode

    @admin.display(description=_("classifier"))
    def classifier_display(self, obj):
        return obj.classifier_id or (obj.config or {}).get("classifier_id", "")

    @staticmethod
    def _pretty(value):
        return format_html('<pre style="white-space: pre-wrap; max-width: 100ch">{}</pre>',
                           json.dumps(value, ensure_ascii=False, indent=2))

    @admin.display(description=_("configuration"))
    def config_pretty(self, obj):
        return self._pretty(obj.config)

    @admin.display(description=_("model version"))
    def model_version_pretty(self, obj):
        return self._pretty(obj.model_version)

    @admin.display(description=_("output"))
    def output_pretty(self, obj):
        return self._pretty(obj.output)


@admin.register(DailyUsage)
class DailyUsageAdmin(admin.ModelAdmin):
    list_display = ("day", "user", "used")
    list_filter = ("day",)
    search_fields = ("user__email",)
    list_select_related = ("user",)
    readonly_fields = ("user", "day")
