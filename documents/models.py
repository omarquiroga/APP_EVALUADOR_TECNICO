import uuid

from django.db import models
from django.db.models import Q

from common.choices import ConfidenceLevel, DocumentStatus
from common.mixins import AppendOnlyVersionMixin, EditableMixin, TimeStampedMixin


class Document(TimeStampedMixin, EditableMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey("procurement.ContractProcess", on_delete=models.CASCADE, related_name="documents")
    bidder = models.ForeignKey("bidders.Bidder", null=True, blank=True, on_delete=models.CASCADE, related_name="documents")
    name = models.CharField(max_length=255)
    document_type = models.CharField(max_length=50)
    classification = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=16, choices=DocumentStatus.choices, default=DocumentStatus.ACTIVE)
    is_required = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "documents_document"
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        indexes = [
            models.Index(fields=["process", "document_type"]),
            models.Index(fields=["bidder", "classification"]),
        ]

    def __str__(self):
        return f"{self.name} [{self.document_type}]"


class DocumentVersion(AppendOnlyVersionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey("documents.Document", on_delete=models.CASCADE, related_name="versions")
    file = models.FileField(upload_to="documents/%Y/%m/%d/")
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, blank=True)
    file_size = models.BigIntegerField(default=0)
    file_hash = models.CharField(max_length=128)
    page_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, choices=DocumentStatus.choices, default=DocumentStatus.ACTIVE)
    is_current = models.BooleanField(default=True)

    class Meta:
        db_table = "documents_document_version"
        verbose_name = "Version de documento"
        verbose_name_plural = "Versiones de documentos"
        constraints = [
            models.UniqueConstraint(fields=["document", "version_no"], name="uq_document_version_number"),
            models.UniqueConstraint(
                fields=["document"],
                condition=Q(is_current=True),
                name="uq_current_document_version_per_document",
            ),
        ]
        indexes = [
            models.Index(fields=["document", "is_current"]),
            models.Index(fields=["file_hash"]),
        ]

    def __str__(self):
        return f"{self.document.name} v{self.version_no}"


class DocumentPageRef(TimeStampedMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document_version = models.ForeignKey("documents.DocumentVersion", on_delete=models.CASCADE, related_name="page_refs")
    page_number = models.PositiveIntegerField()
    label = models.CharField(max_length=255, blank=True)
    extracted_text = models.TextField(blank=True)
    extraction_confidence = models.CharField(
        max_length=20, choices=ConfidenceLevel.choices, default=ConfidenceLevel.NOT_APPLICABLE
    )

    class Meta:
        db_table = "documents_document_page_ref"
        verbose_name = "Referencia de pagina de documento"
        verbose_name_plural = "Referencias de pagina de documento"
        constraints = [
            models.UniqueConstraint(fields=["document_version", "page_number"], name="uq_document_page_ref")
        ]
        indexes = [models.Index(fields=["document_version", "page_number"])]

    def __str__(self):
        return f"{self.document_version} / p.{self.page_number}"
