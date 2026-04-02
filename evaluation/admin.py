from django.contrib import admin

from common.admin import HistoricalAdmin, ReadOnlyTabularInline, SafeReadOnlyAdmin
from .models import ValidationDecisionRecord, ValidationEvidenceLink


class ValidationEvidenceLinkInline(ReadOnlyTabularInline):
    model = ValidationEvidenceLink


@admin.register(ValidationDecisionRecord)
class ValidationDecisionRecordAdmin(HistoricalAdmin):
    @admin.display(description="Sujeto")
    def subject_reference(self, obj):
        field_map = (
            ("bidder", obj.bidder),
            ("bidder_member", obj.bidder_member),
            ("document", obj.document),
            ("rup_record", obj.rup_record),
            ("rup_field_value", obj.rup_field_value),
            ("experience_record", obj.experience_record),
            ("experience_metric", obj.experience_metric),
            ("financial_input_version", obj.financial_input_version),
            ("external_check", obj.external_check),
        )
        for _, value in field_map:
            if value:
                return str(value)
        return "-"

    list_display = (
        "created_at",
        "process",
        "bidder",
        "module",
        "subject_reference",
        "result_code",
        "status",
        "human_confirmed_at",
        "version_no",
    )
    list_filter = (
        "module",
        "subject_type",
        "result_code",
        "status",
        "human_required",
        "reevaluation_required",
        "confidence_level",
    )
    search_fields = (
        "process__code",
        "bidder__name",
        "rule_definition__code",
        "rule_definition__name",
        "subject_uuid",
        "human_decision_note",
        "obsolete_reason",
    )
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    fieldsets = (
        ("Contexto", {"fields": ("process", "bidder", "module", "subject_type", "subject_uuid")}),
        ("Regla", {"fields": ("rule_definition", "rule_version", "normative_snapshot")}),
        (
            "Sujeto evaluado",
            {
                "fields": (
                    "bidder_member",
                    "document",
                    "rup_record",
                    "rup_field_value",
                    "experience_record",
                    "experience_metric",
                    "financial_input_version",
                    "external_check",
                )
            },
        ),
        (
            "Resultado",
            {
                "fields": (
                    "result_code",
                    "status",
                    "confidence_level",
                    "human_required",
                    "reevaluation_required",
                    "result_value",
                )
            },
        ),
        (
            "Revision humana",
            {
                "fields": (
                    "human_confirmed_by",
                    "human_confirmed_at",
                    "human_decision_note",
                    "obsolete_reason",
                )
            },
        ),
        ("Trazabilidad tecnica", {"fields": ("input_payload", "logic_trace"), "classes": ("collapse",)}),
        ("Versionado", {"fields": ("version_no", "supersedes", "created_at", "created_by")}),
    )
    inlines = [ValidationEvidenceLinkInline]


@admin.register(ValidationEvidenceLink)
class ValidationEvidenceLinkAdmin(SafeReadOnlyAdmin):
    list_display = ("validation_decision", "document_version", "document_page_ref", "evidence_role", "created_at")
    list_filter = ("evidence_role",)
    search_fields = ("validation_decision__process__code", "document_version__original_filename", "note")
    ordering = ("-created_at",)
