from django.contrib import admin

from common.admin import HistoricalAdmin, SafeReadOnlyAdmin
from .models import (
    DocumentTypeArtifact,
    DocumentTypeFamily,
    DocumentTypeVersion,
    NormativeSnapshot,
    NormativeSource,
    ProcessNormativeBinding,
)


class DocumentTypeVersionInline(admin.TabularInline):
    model = DocumentTypeVersion
    extra = 0


class DocumentTypeArtifactInline(admin.TabularInline):
    model = DocumentTypeArtifact
    extra = 0


@admin.register(NormativeSource)
class NormativeSourceAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "homepage_url", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    readonly_fields = ("created_at", "created_by")


@admin.register(DocumentTypeFamily)
class DocumentTypeFamilyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "source", "sector", "modality", "is_active")
    list_filter = ("is_active", "sector", "modality", "source")
    search_fields = ("code", "name")
    readonly_fields = ("created_at", "created_by")
    inlines = [DocumentTypeVersionInline]


@admin.register(DocumentTypeVersion)
class DocumentTypeVersionAdmin(admin.ModelAdmin):
    list_display = ("family", "version_label", "resolution_reference", "valid_from", "valid_to", "is_active")
    list_filter = ("is_active", "family__sector", "family__modality")
    search_fields = ("family__name", "version_label", "resolution_reference")
    readonly_fields = ("created_at", "created_by")
    inlines = [DocumentTypeArtifactInline]


@admin.register(DocumentTypeArtifact)
class DocumentTypeArtifactAdmin(admin.ModelAdmin):
    list_display = ("name", "artifact_type", "version", "official_url")
    list_filter = ("artifact_type",)
    search_fields = ("name", "version__version_label", "version__family__name")
    readonly_fields = ("created_at", "created_by")


@admin.register(ProcessNormativeBinding)
class ProcessNormativeBindingAdmin(admin.ModelAdmin):
    list_display = ("process", "document_type_version", "current_snapshot", "updated_at")
    list_filter = ("document_type_version__family",)
    search_fields = ("process__code", "process__name", "document_type_version__version_label")
    readonly_fields = ("created_at", "created_by", "updated_at", "updated_by", "row_version")


@admin.register(NormativeSnapshot)
class NormativeSnapshotAdmin(HistoricalAdmin):
    list_display = ("process", "document_type_version", "snapshot_label", "version_no", "is_current", "created_at")
    list_filter = ("is_current", "document_type_version__family")
    search_fields = ("process__code", "process__name", "snapshot_label", "checksum")
