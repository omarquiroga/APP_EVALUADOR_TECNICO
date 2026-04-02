from django.contrib import admin

from common.admin import SafeReadOnlyAdmin
from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(SafeReadOnlyAdmin):
    @admin.display(description="Objeto")
    def object_reference(self, obj):
        return f"{obj.object_type} / {str(obj.object_uuid)[:8]}"

    list_display = ("created_at", "module", "event_type", "action", "process", "bidder", "object_reference")
    list_filter = ("module", "event_type", "action", "created_by")
    search_fields = ("process__code", "bidder__name", "object_type", "object_uuid", "event_type", "action")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    readonly_fields = (
        "created_at",
        "created_by",
        "process",
        "bidder",
        "event_type",
        "module",
        "object_type",
        "object_uuid",
        "action",
        "before_payload",
        "after_payload",
        "metadata",
    )
    fieldsets = (
        ("Evento", {"fields": ("created_at", "created_by", "module", "event_type", "action")}),
        ("Contexto", {"fields": ("process", "bidder", "object_type", "object_uuid")}),
        ("Payloads", {"fields": ("before_payload", "after_payload", "metadata"), "classes": ("collapse",)}),
    )
