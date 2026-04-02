from django.contrib import admin

from common.admin import AddOnlyAdmin, HistoricalAdmin, ReadOnlyTabularInline
from .models import (
    ExperienceAssessment,
    ExperienceConsolidation,
    ExperienceMetric,
    ExperienceRecord,
    MinimumWageYear,
    SMMLVConversionRecord,
)


class ExperienceMetricInline(ReadOnlyTabularInline):
    model = ExperienceMetric
    fields = ("metric_code", "metric_value_number", "metric_unit", "source", "document_page_ref", "version_no")


@admin.register(ExperienceRecord)
class ExperienceRecordAdmin(AddOnlyAdmin):
    list_display = (
        "created_at",
        "process",
        "contract_identifier",
        "bidder",
        "bidder_member",
        "contract_type",
        "contract_year",
        "review_status",
        "version_no",
    )
    list_filter = ("review_status", "contract_type", "contract_year", "is_general_experience_candidate", "is_specific_experience_candidate")
    search_fields = ("contract_identifier", "bidder__name", "contract_object")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "created_by", "version_no", "supersedes")
    fieldsets = (
        ("Contexto", {"fields": ("process", "bidder", "bidder_member", "review_status")}),
        ("Contrato", {"fields": ("contract_identifier", "contract_type", "contract_object", "contractor_role")}),
        ("Valores y fechas", {"fields": ("contract_value_nominal", "contract_currency", "contract_year", "execution_start_date", "execution_end_date")}),
        (
            "Parametros de evaluacion",
            {
                "fields": (
                    "execution_length_value",
                    "execution_length_unit",
                    "participation_percentage",
                    "is_general_experience_candidate",
                    "is_specific_experience_candidate",
                )
            },
        ),
        ("Soporte", {"fields": ("source_document",)}),
        ("Versionado", {"fields": ("version_no", "supersedes", "created_at", "created_by")}),
    )
    inlines = [ExperienceMetricInline]


@admin.register(ExperienceMetric)
class ExperienceMetricAdmin(HistoricalAdmin):
    list_display = ("experience_record", "metric_code", "metric_value_number", "metric_unit", "source", "version_no")
    list_filter = ("metric_code", "source")
    search_fields = ("experience_record__contract_identifier", "metric_code")


@admin.register(MinimumWageYear)
class MinimumWageYearAdmin(admin.ModelAdmin):
    list_display = ("year", "amount", "is_active")
    list_filter = ("is_active",)
    search_fields = ("year",)
    readonly_fields = ("created_at", "created_by", "updated_at", "updated_by", "row_version")


@admin.register(SMMLVConversionRecord)
class SMMLVConversionRecordAdmin(HistoricalAdmin):
    list_display = ("experience_record", "minimum_wage_year", "source_value", "resulting_smmlv", "version_no")
    list_filter = ("minimum_wage_year",)
    search_fields = ("experience_record__contract_identifier",)


@admin.register(ExperienceAssessment)
class ExperienceAssessmentAdmin(HistoricalAdmin):
    list_display = ("experience_record", "bidder", "scope", "is_valid", "rule_definition", "version_no")
    list_filter = ("scope", "is_valid")
    search_fields = ("experience_record__contract_identifier", "bidder__name", "rule_definition__code")


@admin.register(ExperienceConsolidation)
class ExperienceConsolidationAdmin(HistoricalAdmin):
    list_display = ("bidder", "process", "scope", "total_valid_contracts", "meets_requirement", "status", "version_no")
    list_filter = ("scope", "meets_requirement", "status")
    search_fields = ("bidder__name", "process__code")
