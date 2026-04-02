from django.contrib import admin

from common.admin import HistoricalAdmin, ReadOnlyTabularInline
from .models import Document, DocumentPageRef, DocumentVersion


class DocumentVersionInline(ReadOnlyTabularInline):
    model = DocumentVersion
    fields = ("original_filename", "file_hash", "page_count", "status", "is_current", "version_no")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("name", "process", "bidder", "document_type", "classification", "status", "is_required")
    list_filter = ("status", "document_type", "classification", "is_required")
    search_fields = ("name", "process__code", "bidder__name")
    readonly_fields = ("created_at", "created_by", "updated_at", "updated_by", "row_version")
    inlines = [DocumentVersionInline]


@admin.register(DocumentVersion)
class DocumentVersionAdmin(HistoricalAdmin):
    @admin.display(description="Proceso")
    def process_reference(self, obj):
        return obj.document.process

    @admin.display(description="Proponente")
    def bidder_reference(self, obj):
        return obj.document.bidder or "-"

    list_display = (
        "created_at",
        "process_reference",
        "bidder_reference",
        "document",
        "version_no",
        "is_current",
        "status",
        "page_count",
    )
    list_filter = ("is_current", "status", "document__document_type")
    search_fields = ("original_filename", "file_hash", "document__name", "document__bidder__name", "document__process__code")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    fieldsets = (
        ("Documento", {"fields": ("document", "original_filename", "status", "is_current")}),
        ("Archivo", {"fields": ("content_type", "file_size", "file_hash", "page_count")}),
        ("Soporte", {"fields": ("file",)}),
        ("Versionado", {"fields": ("version_no", "supersedes", "created_at", "created_by")}),
    )


@admin.register(DocumentPageRef)
class DocumentPageRefAdmin(admin.ModelAdmin):
    list_display = ("document_version", "page_number", "label", "extraction_confidence", "created_at")
    list_filter = ("extraction_confidence",)
    search_fields = ("document_version__original_filename", "label", "extracted_text")
    readonly_fields = ("created_at", "created_by")

    def has_delete_permission(self, request, obj=None):
        return False
