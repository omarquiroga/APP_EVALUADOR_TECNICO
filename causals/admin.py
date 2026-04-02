from django.contrib import admin

from common.admin import HistoricalAdmin
from .models import RejectionCauseAssessment, RejectionCauseDefinition


@admin.register(RejectionCauseDefinition)
class RejectionCauseDefinitionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "process", "is_subsanable", "severity", "human_required", "is_active")
    list_filter = ("is_subsanable", "severity", "human_required", "is_active")
    search_fields = ("code", "name", "process__code", "description")
    readonly_fields = ("created_at", "created_by", "updated_at", "updated_by", "row_version")


@admin.register(RejectionCauseAssessment)
class RejectionCauseAssessmentAdmin(HistoricalAdmin):
    list_display = (
        "created_at",
        "process",
        "bidder",
        "cause_definition",
        "status",
        "reviewed_at",
        "human_review_required",
        "impact_on_closure",
        "version_no",
    )
    list_filter = (
        "status",
        "origin_type",
        "is_subsanable",
        "human_review_required",
        "impact_on_closure",
        "cause_definition",
    )
    search_fields = ("process__code", "bidder__name", "cause_definition__code", "cause_definition__name", "decision_note", "evidence_summary")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    fieldsets = (
        ("Contexto", {"fields": ("process", "bidder", "cause_definition", "status", "origin_type")}),
        ("Origen", {"fields": ("triggering_decision_record", "is_subsanable", "human_review_required")}),
        ("Decision", {"fields": ("impact_on_closure", "impact_on_final_status", "decision_note")}),
        ("Soporte", {"fields": ("evidence_summary",), "classes": ("collapse",)}),
        ("Revision", {"fields": ("reviewed_by", "reviewed_at")}),
        ("Versionado", {"fields": ("version_no", "supersedes", "created_at", "created_by")}),
    )
