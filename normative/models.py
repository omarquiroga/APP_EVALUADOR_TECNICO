import uuid

from django.db import models
from django.db.models import Q

from common.mixins import AppendOnlyVersionMixin, EditableMixin, TimeStampedMixin


class NormativeSource(TimeStampedMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    homepage_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "normative_source"
        verbose_name = "Fuente normativa"
        verbose_name_plural = "Fuentes normativas"


class DocumentTypeFamily(TimeStampedMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey("normative.NormativeSource", on_delete=models.PROTECT, related_name="families")
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    sector = models.CharField(max_length=100, blank=True)
    modality = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "normative_document_type_family"
        verbose_name = "Familia de documento tipo"
        verbose_name_plural = "Familias de documentos tipo"
        indexes = [models.Index(fields=["sector", "modality"])]


class DocumentTypeVersion(TimeStampedMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family = models.ForeignKey("normative.DocumentTypeFamily", on_delete=models.PROTECT, related_name="versions")
    version_label = models.CharField(max_length=100)
    resolution_reference = models.CharField(max_length=255, blank=True)
    official_url = models.URLField(blank=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "normative_document_type_version"
        verbose_name = "Version de documento tipo"
        verbose_name_plural = "Versiones de documentos tipo"
        constraints = [
            models.UniqueConstraint(fields=["family", "version_label"], name="uq_document_type_version_label")
        ]
        indexes = [
            models.Index(fields=["family", "is_active"]),
            models.Index(fields=["valid_from", "valid_to"]),
        ]


class DocumentTypeArtifact(TimeStampedMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.ForeignKey("normative.DocumentTypeVersion", on_delete=models.CASCADE, related_name="artifacts")
    name = models.CharField(max_length=255)
    artifact_type = models.CharField(max_length=50)
    official_url = models.URLField(blank=True)
    file_hash = models.CharField(max_length=128, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "normative_document_type_artifact"
        verbose_name = "Artefacto normativo"
        verbose_name_plural = "Artefactos normativos"
        indexes = [models.Index(fields=["version", "artifact_type"])]


class NormativeSnapshot(AppendOnlyVersionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey("procurement.ContractProcess", on_delete=models.PROTECT, related_name="normative_snapshots")
    document_type_version = models.ForeignKey(
        "normative.DocumentTypeVersion", on_delete=models.PROTECT, related_name="snapshots"
    )
    snapshot_label = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    checksum = models.CharField(max_length=128)
    is_current = models.BooleanField(default=True)

    class Meta:
        db_table = "normative_snapshot"
        verbose_name = "Snapshot normativo"
        verbose_name_plural = "Snapshots normativos"
        constraints = [
            models.UniqueConstraint(fields=["process", "version_no"], name="uq_normative_snapshot_process_version"),
            models.UniqueConstraint(
                fields=["process"],
                condition=Q(is_current=True),
                name="uq_current_normative_snapshot_per_process",
            ),
        ]
        indexes = [models.Index(fields=["process", "is_current"])]


class ProcessNormativeBinding(TimeStampedMixin, EditableMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.OneToOneField("procurement.ContractProcess", on_delete=models.CASCADE, related_name="normative_binding")
    document_type_version = models.ForeignKey(
        "normative.DocumentTypeVersion", on_delete=models.PROTECT, related_name="process_bindings"
    )
    current_snapshot = models.ForeignKey(
        "normative.NormativeSnapshot",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="current_for_bindings",
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "procurement_process_normative_binding"
        verbose_name = "Vinculo normativo del proceso"
        verbose_name_plural = "Vinculos normativos del proceso"
