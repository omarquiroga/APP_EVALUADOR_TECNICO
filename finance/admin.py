from django.contrib import admin

from common.admin import AddOnlyAdmin, HistoricalAdmin
from .models import FinancialAssessment, FinancialInputVersion


@admin.register(FinancialInputVersion)
class FinancialInputVersionAdmin(AddOnlyAdmin):
    list_display = ("source_date", "process", "bidder", "source_label", "status", "version_no")
    list_filter = ("status", "source_date")
    search_fields = ("bidder__name", "process__code", "source_label", "financial_observation")
    ordering = ("-source_date", "-version_no")
    date_hierarchy = "source_date"
    readonly_fields = ("created_at", "created_by", "version_no", "supersedes")
    fieldsets = (
        ("Contexto", {"fields": ("process", "bidder", "status")}),
        ("Fuente", {"fields": ("source_label", "source_document", "source_date")}),
        ("Valores", {"fields": ("assets_value", "liabilities_value", "operating_income_value")}),
        ("Detalle", {"fields": ("financial_observation", "raw_payload"), "classes": ("collapse",)}),
        ("Versionado", {"fields": ("version_no", "supersedes", "created_at", "created_by")}),
    )


@admin.register(FinancialAssessment)
class FinancialAssessmentAdmin(HistoricalAdmin):
    list_display = (
        "created_at",
        "process",
        "bidder",
        "result_code",
        "status",
        "used_in_consolidation",
        "reviewed_at",
        "version_no",
    )
    list_filter = ("result_code", "status", "used_in_consolidation", "human_required")
    search_fields = ("bidder__name", "process__code", "financial_input_version__source_label", "assessment_note")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    fieldsets = (
        ("Contexto", {"fields": ("process", "bidder", "financial_input_version")}),
        ("Resultado", {"fields": ("result_code", "status", "used_in_consolidation", "human_required")}),
        ("Revision", {"fields": ("reviewed_by", "reviewed_at", "assessment_note")}),
        ("Versionado", {"fields": ("version_no", "supersedes", "created_at", "created_by")}),
    )
