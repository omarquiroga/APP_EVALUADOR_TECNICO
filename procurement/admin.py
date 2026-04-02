from django.contrib import admin

from .models import ContractProcess, ProcessTeamMember


class ProcessTeamMemberInline(admin.TabularInline):
    model = ProcessTeamMember
    extra = 0


@admin.register(ContractProcess)
class ContractProcessAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "entity_name", "process_type", "modality", "state", "opening_date", "closing_date")
    list_filter = ("state", "process_type", "modality")
    search_fields = ("code", "name", "entity_name", "reference_number")
    inlines = [ProcessTeamMemberInline]
    readonly_fields = ("created_at", "created_by", "updated_at", "updated_by", "row_version")
    fieldsets = (
        ("Identificacion", {"fields": ("code", "name", "reference_number", "entity_name")}),
        ("Clasificacion", {"fields": ("process_type", "modality", "state")}),
        ("Fechas", {"fields": ("opening_date", "closing_date")}),
        ("Contexto", {"fields": ("description", "current_rule_bundle_version")}),
        ("Auditoria", {"fields": ("created_at", "created_by", "updated_at", "updated_by", "row_version")}),
    )


@admin.register(ProcessTeamMember)
class ProcessTeamMemberAdmin(admin.ModelAdmin):
    list_display = ("process", "user", "role_code", "is_active", "created_at")
    list_filter = ("role_code", "is_active")
    search_fields = ("process__code", "process__name", "user__username", "user__email")
    readonly_fields = ("created_at", "created_by")
