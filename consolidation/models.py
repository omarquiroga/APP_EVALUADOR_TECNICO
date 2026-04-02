import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from common.choices import ResultCode
from common.mixins import AppendOnlyVersionMixin


class ConsolidatedMatrixSnapshot(AppendOnlyVersionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey("procurement.ContractProcess", on_delete=models.PROTECT, related_name="matrix_snapshots")
    normative_snapshot = models.ForeignKey(
        "normative.NormativeSnapshot", on_delete=models.PROTECT, related_name="matrix_snapshots"
    )
    generated_by = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="matrix_snapshots_generated"
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    snapshot_label = models.CharField(max_length=100)
    data_fingerprint = models.CharField(max_length=128)
    serialized_matrix_payload = models.JSONField(default=dict)
    is_current = models.BooleanField(default=True)

    class Meta:
        db_table = "consolidation_matrix_snapshot"
        verbose_name = "Snapshot de matriz consolidada"
        verbose_name_plural = "Snapshots de matrices consolidadas"
        constraints = [
            models.UniqueConstraint(fields=["process", "version_no"], name="uq_matrix_snapshot_process_version"),
            models.UniqueConstraint(
                fields=["process"],
                condition=Q(is_current=True),
                name="uq_current_matrix_snapshot_per_process",
            ),
        ]
        indexes = [models.Index(fields=["process", "is_current"])]

    def __str__(self):
        return f"{self.process.code} / {self.snapshot_label} / v{self.version_no}"


class BidderConsolidatedResult(AppendOnlyVersionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey("procurement.ContractProcess", on_delete=models.PROTECT, related_name="bidder_consolidated_results")
    bidder = models.ForeignKey("bidders.Bidder", on_delete=models.PROTECT, related_name="consolidated_results")
    matrix_snapshot = models.ForeignKey(
        "consolidation.ConsolidatedMatrixSnapshot",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="bidder_results",
    )
    technical_result = models.CharField(max_length=20, choices=ResultCode.choices, default=ResultCode.PENDING)
    rup_result = models.CharField(max_length=20, choices=ResultCode.choices, default=ResultCode.PENDING)
    experience_general_result = models.CharField(max_length=20, choices=ResultCode.choices, default=ResultCode.PENDING)
    experience_specific_result = models.CharField(max_length=20, choices=ResultCode.choices, default=ResultCode.PENDING)
    financial_result = models.CharField(max_length=20, choices=ResultCode.choices, default=ResultCode.PENDING)
    rejection_result = models.CharField(max_length=20, choices=ResultCode.choices, default=ResultCode.PENDING)
    final_result = models.CharField(max_length=20, choices=ResultCode.choices, default=ResultCode.PENDING)
    observations = models.TextField(blank=True)
    trace_payload = models.JSONField(default=dict)

    def clean(self):
        errors = {}

        if self.bidder_id and self.bidder.process_id != self.process_id:
            errors["bidder"] = "El proponente no pertenece al proceso indicado."

        if self.matrix_snapshot_id and self.matrix_snapshot.process_id != self.process_id:
            errors["matrix_snapshot"] = "El snapshot de matriz pertenece a otro proceso."

        if errors:
            raise ValidationError(errors)

    class Meta:
        db_table = "consolidation_bidder_consolidated_result"
        verbose_name = "Resultado consolidado por proponente"
        verbose_name_plural = "Resultados consolidados por proponente"
        indexes = [
            models.Index(fields=["process", "bidder"]),
            models.Index(fields=["final_result"]),
        ]

    def __str__(self):
        return f"{self.bidder} / {self.final_result} / v{self.version_no}"


class FinalReportVersion(AppendOnlyVersionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey("procurement.ContractProcess", on_delete=models.PROTECT, related_name="final_report_versions")
    matrix_snapshot = models.ForeignKey(
        "consolidation.ConsolidatedMatrixSnapshot",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="final_report_versions",
    )
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=20, default="draft")
    file = models.FileField(upload_to="reports/%Y/%m/%d/", null=True, blank=True)
    file_hash = models.CharField(max_length=128, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "reports_final_report_version"
        verbose_name = "Version de informe final"
        verbose_name_plural = "Versiones de informes finales"
        indexes = [models.Index(fields=["process", "version_no"])]

    def __str__(self):
        return f"{self.process.code} / {self.title} / v{self.version_no}"
