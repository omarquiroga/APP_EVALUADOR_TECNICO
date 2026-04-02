import uuid

from django.db import models

from common.choices import ValidationStatus
from common.mixins import AppendOnlyVersionMixin, EditableMixin, TimeStampedMixin


class RUPRecord(AppendOnlyVersionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey("procurement.ContractProcess", on_delete=models.PROTECT, related_name="rup_records")
    bidder = models.ForeignKey("bidders.Bidder", on_delete=models.PROTECT, related_name="rup_records")
    source_document = models.ForeignKey(
        "documents.DocumentVersion", null=True, blank=True, on_delete=models.PROTECT, related_name="rup_records"
    )
    record_date = models.DateField(null=True, blank=True)
    issuer = models.CharField(max_length=255, blank=True)
    validity_note = models.TextField(blank=True)
    raw_extracted_payload = models.JSONField(default=dict)
    review_status = models.CharField(max_length=32, choices=ValidationStatus.choices, default=ValidationStatus.NOT_EVALUATED)

    class Meta:
        db_table = "rup_rup_record"
        verbose_name = "Registro RUP"
        verbose_name_plural = "Registros RUP"
        constraints = [models.UniqueConstraint(fields=["bidder", "version_no"], name="uq_rup_record_bidder_version")]
        indexes = [models.Index(fields=["process", "bidder"])]

    def __str__(self):
        return f"RUP {self.bidder} v{self.version_no}"


class RUPFieldSchema(TimeStampedMixin, EditableMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=100, unique=True)
    label = models.CharField(max_length=255)
    data_type = models.CharField(max_length=30)
    is_required = models.BooleanField(default=False)
    validation_hint = models.CharField(max_length=255, blank=True)
    applies_to_process_type = models.CharField(max_length=100, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "rup_rup_field_schema"
        verbose_name = "Esquema de campo RUP"
        verbose_name_plural = "Esquemas de campos RUP"
        indexes = [models.Index(fields=["is_active", "sort_order"])]

    def __str__(self):
        return f"{self.code} - {self.label}"


class RUPFieldValue(AppendOnlyVersionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rup_record = models.ForeignKey("rup.RUPRecord", on_delete=models.CASCADE, related_name="field_values")
    schema = models.ForeignKey("rup.RUPFieldSchema", on_delete=models.PROTECT, related_name="values")
    value_text = models.TextField(blank=True)
    value_number = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    value_json = models.JSONField(default=dict, blank=True)
    document_page_ref = models.ForeignKey(
        "documents.DocumentPageRef", null=True, blank=True, on_delete=models.PROTECT, related_name="rup_field_values"
    )

    class Meta:
        db_table = "rup_rup_field_value"
        verbose_name = "Valor de campo RUP"
        verbose_name_plural = "Valores de campos RUP"
        constraints = [
            models.UniqueConstraint(fields=["rup_record", "schema", "version_no"], name="uq_rup_field_value_version")
        ]
        indexes = [models.Index(fields=["rup_record", "schema"])]

    def __str__(self):
        return f"{self.rup_record} / {self.schema.code} / v{self.version_no}"


class RUPSegmentEntry(AppendOnlyVersionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rup_record = models.ForeignKey("rup.RUPRecord", on_delete=models.CASCADE, related_name="segments")
    segment_code = models.CharField(max_length=50)
    description = models.CharField(max_length=255, blank=True)
    document_page_ref = models.ForeignKey(
        "documents.DocumentPageRef", null=True, blank=True, on_delete=models.PROTECT, related_name="rup_segments"
    )

    class Meta:
        db_table = "rup_rup_segment_entry"
        verbose_name = "Entrada de segmento RUP"
        verbose_name_plural = "Entradas de segmentos RUP"
        indexes = [models.Index(fields=["rup_record", "segment_code"])]

    def __str__(self):
        return f"{self.rup_record} / seg {self.segment_code}"


class RUPCodeEntry(AppendOnlyVersionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rup_record = models.ForeignKey("rup.RUPRecord", on_delete=models.CASCADE, related_name="codes")
    code_type = models.CharField(max_length=50)
    code_value = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    document_page_ref = models.ForeignKey(
        "documents.DocumentPageRef", null=True, blank=True, on_delete=models.PROTECT, related_name="rup_codes"
    )

    class Meta:
        db_table = "rup_rup_code_entry"
        verbose_name = "Entrada de codigo RUP"
        verbose_name_plural = "Entradas de codigos RUP"
        indexes = [models.Index(fields=["rup_record", "code_type", "code_value"])]

    def __str__(self):
        return f"{self.rup_record} / {self.code_type}:{self.code_value}"
