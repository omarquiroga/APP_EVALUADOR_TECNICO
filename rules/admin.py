from django.contrib import admin

from common.admin import HistoricalAdmin
from .models import ProcessRuleActivation, RuleDefinition, RuleVersion


class RuleVersionInline(admin.TabularInline):
    model = RuleVersion
    extra = 0
    fields = ("version_label", "process", "severity", "is_active", "human_required", "version_no")
    readonly_fields = ("version_no",)


@admin.register(RuleDefinition)
class RuleDefinitionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "module", "rule_type", "is_active", "default_human_required")
    list_filter = ("module", "rule_type", "is_active", "default_human_required")
    search_fields = ("code", "name", "description")
    readonly_fields = ("created_at", "created_by", "updated_at", "updated_by", "row_version")
    inlines = [RuleVersionInline]


@admin.register(RuleVersion)
class RuleVersionAdmin(HistoricalAdmin):
    list_display = ("rule_definition", "version_label", "process", "severity", "is_active", "version_no", "created_at")
    list_filter = ("is_active", "severity", "human_required", "process")
    search_fields = ("rule_definition__code", "rule_definition__name", "version_label", "checksum")


@admin.register(ProcessRuleActivation)
class ProcessRuleActivationAdmin(admin.ModelAdmin):
    list_display = ("process", "rule_definition", "rule_version", "is_active", "updated_at")
    list_filter = ("is_active", "rule_definition__module")
    search_fields = ("process__code", "rule_definition__code", "rule_definition__name", "rule_version__version_label")
    readonly_fields = ("created_at", "created_by", "updated_at", "updated_by", "row_version")
