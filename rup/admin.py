from django.contrib import admin

from common.admin import AddOnlyAdmin, HistoricalAdmin, ReadOnlyTabularInline
from .models import RUPCodeEntry, RUPFieldSchema, RUPFieldValue, RUPRecord, RUPSegmentEntry


class RUPFieldValueInline(ReadOnlyTabularInline):
    model = RUPFieldValue
    fields = ("schema", "value_text", "value_number", "document_page_ref", "version_no")


@admin.register(RUPRecord)
class RUPRecordAdmin(AddOnlyAdmin):
    list_display = ("record_date", "process", "bidder", "issuer", "review_status", "version_no")
    list_filter = ("review_status",)
    search_fields = ("bidder__name", "process__code", "issuer", "validity_note")
    ordering = ("-record_date", "-version_no")
    date_hierarchy = "record_date"
    readonly_fields = ("created_at", "created_by", "version_no", "supersedes")
    fieldsets = (
        ("Contexto", {"fields": ("process", "bidder", "review_status")}),
        ("Fuente", {"fields": ("source_document", "record_date", "issuer")}),
        ("Revision", {"fields": ("validity_note",)}),
        ("Contenido extraido", {"fields": ("raw_extracted_payload",), "classes": ("collapse",)}),
        ("Versionado", {"fields": ("version_no", "supersedes", "created_at", "created_by")}),
    )
    inlines = [RUPFieldValueInline]


@admin.register(RUPFieldSchema)
class RUPFieldSchemaAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "data_type", "is_required", "is_active", "sort_order")
    list_filter = ("data_type", "is_required", "is_active")
    search_fields = ("code", "label", "validation_hint", "applies_to_process_type")
    readonly_fields = ("created_at", "created_by", "updated_at", "updated_by", "row_version")


@admin.register(RUPFieldValue)
class RUPFieldValueAdmin(HistoricalAdmin):
    list_display = ("rup_record", "schema", "value_text", "value_number", "version_no")
    list_filter = ("schema",)
    search_fields = ("rup_record__bidder__name", "schema__code", "schema__label", "value_text")


@admin.register(RUPSegmentEntry)
class RUPSegmentEntryAdmin(HistoricalAdmin):
    list_display = ("rup_record", "segment_code", "description", "version_no")
    list_filter = ("segment_code",)
    search_fields = ("rup_record__bidder__name", "segment_code", "description")


@admin.register(RUPCodeEntry)
class RUPCodeEntryAdmin(HistoricalAdmin):
    list_display = ("rup_record", "code_type", "code_value", "description", "version_no")
    list_filter = ("code_type",)
    search_fields = ("rup_record__bidder__name", "code_type", "code_value", "description")
