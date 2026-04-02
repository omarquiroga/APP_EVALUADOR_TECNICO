from django.contrib import admin

from common.admin import HistoricalAdmin, ReadOnlyTabularInline
from .models import BidderConsolidatedResult, ConsolidatedMatrixSnapshot, FinalReportVersion


class BidderConsolidatedResultInline(ReadOnlyTabularInline):
    model = BidderConsolidatedResult
    fields = ("bidder", "final_result", "technical_result", "financial_result", "rejection_result", "version_no")


@admin.register(ConsolidatedMatrixSnapshot)
class ConsolidatedMatrixSnapshotAdmin(HistoricalAdmin):
    list_display = ("generated_at", "process", "snapshot_label", "is_current", "generated_by", "version_no")
    list_filter = ("is_current",)
    search_fields = ("process__code", "snapshot_label", "data_fingerprint", "normative_snapshot__snapshot_label")
    ordering = ("-generated_at",)
    date_hierarchy = "generated_at"
    fieldsets = (
        ("Contexto", {"fields": ("process", "normative_snapshot", "snapshot_label", "is_current")}),
        ("Generacion", {"fields": ("generated_by", "generated_at", "data_fingerprint")}),
        ("Payload", {"fields": ("serialized_matrix_payload",), "classes": ("collapse",)}),
        ("Versionado", {"fields": ("version_no", "supersedes", "created_at", "created_by")}),
    )
    inlines = [BidderConsolidatedResultInline]


@admin.register(BidderConsolidatedResult)
class BidderConsolidatedResultAdmin(HistoricalAdmin):
    list_display = (
        "created_at",
        "process",
        "bidder",
        "final_result",
        "technical_result",
        "financial_result",
        "rejection_result",
        "version_no",
    )
    list_filter = ("final_result", "technical_result", "financial_result", "rejection_result")
    search_fields = ("process__code", "bidder__name", "observations")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    fieldsets = (
        ("Contexto", {"fields": ("process", "bidder", "matrix_snapshot")}),
        ("Resultado final", {"fields": ("final_result", "rejection_result", "observations")}),
        (
            "Resultados por dimension",
            {
                "fields": (
                    "technical_result",
                    "rup_result",
                    "experience_general_result",
                    "experience_specific_result",
                    "financial_result",
                )
            },
        ),
        ("Trazabilidad", {"fields": ("trace_payload",), "classes": ("collapse",)}),
        ("Versionado", {"fields": ("version_no", "supersedes", "created_at", "created_by")}),
    )


@admin.register(FinalReportVersion)
class FinalReportVersionAdmin(HistoricalAdmin):
    list_display = ("created_at", "process", "title", "status", "matrix_snapshot", "version_no")
    list_filter = ("status",)
    search_fields = ("process__code", "title", "file_hash")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    fieldsets = (
        ("Contexto", {"fields": ("process", "matrix_snapshot", "title", "status")}),
        ("Archivo", {"fields": ("file", "file_hash")}),
        ("Payload", {"fields": ("payload",), "classes": ("collapse",)}),
        ("Versionado", {"fields": ("version_no", "supersedes", "created_at", "created_by")}),
    )
