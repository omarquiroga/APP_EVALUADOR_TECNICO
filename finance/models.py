import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from common.choices import FinancialAssessmentStatus, FinancialInputStatus, ResultCode
from common.mixins import AppendOnlyVersionMixin


class FinancialInputVersion(AppendOnlyVersionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey("procurement.ContractProcess", on_delete=models.PROTECT, related_name="financial_inputs")
    bidder = models.ForeignKey("bidders.Bidder", on_delete=models.PROTECT, related_name="financial_inputs")
    source_label = models.CharField(max_length=255)
    source_document = models.ForeignKey(
        "documents.DocumentVersion", null=True, blank=True, on_delete=models.PROTECT, related_name="financial_inputs"
    )
    source_date = models.DateField()
    assets_value = models.DecimalField(max_digits=20, decimal_places=2)
    liabilities_value = models.DecimalField(max_digits=20, decimal_places=2)
    operating_income_value = models.DecimalField(max_digits=20, decimal_places=2)
    raw_payload = models.JSONField(default=dict, blank=True)
    financial_observation = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=FinancialInputStatus.choices, default=FinancialInputStatus.DRAFT)

    class Meta:
        db_table = "finance_financial_input_version"
        verbose_name = "Version de insumo financiero"
        verbose_name_plural = "Versiones de insumos financieros"
        constraints = [
            models.UniqueConstraint(fields=["bidder", "version_no"], name="uq_financial_input_bidder_version"),
            models.UniqueConstraint(
                fields=["bidder"],
                condition=Q(status=FinancialInputStatus.DRAFT),
                name="uq_single_financial_input_draft_per_bidder",
            ),
        ]
        indexes = [
            models.Index(fields=["process", "bidder", "status"]),
            models.Index(fields=["source_date"]),
        ]

    def __str__(self):
        return f"{self.bidder} / fin-input v{self.version_no} / {self.status}"


class FinancialAssessment(AppendOnlyVersionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey("procurement.ContractProcess", on_delete=models.PROTECT, related_name="financial_assessments")
    bidder = models.ForeignKey("bidders.Bidder", on_delete=models.PROTECT, related_name="financial_assessments")
    financial_input_version = models.ForeignKey(
        "finance.FinancialInputVersion", on_delete=models.PROTECT, related_name="assessments"
    )
    result_code = models.CharField(max_length=20, choices=ResultCode.choices, default=ResultCode.PENDING)
    status = models.CharField(max_length=16, choices=FinancialAssessmentStatus.choices, default=FinancialAssessmentStatus.PRELIMINAR)
    assessment_note = models.TextField(blank=True)
    human_required = models.BooleanField(default=True)
    reviewed_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="financial_assessments_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    used_in_consolidation = models.BooleanField(default=False)

    def clean(self):
        errors = {}
        if self.financial_input_version_id:
            if self.financial_input_version.bidder_id != self.bidder_id:
                errors["financial_input_version"] = "El input financiero pertenece a otro proponente."
            if self.financial_input_version.process_id != self.process_id:
                errors["financial_input_version"] = "El input financiero pertenece a otro proceso."
        if self.used_in_consolidation and self.status != FinancialAssessmentStatus.CONFIRMED:
            errors["used_in_consolidation"] = "Solo una evaluacion financiera confirmada puede usarse en consolidacion."
        if errors:
            raise ValidationError(errors)

    class Meta:
        db_table = "finance_financial_assessment"
        verbose_name = "Evaluacion financiera"
        verbose_name_plural = "Evaluaciones financieras"
        constraints = [
            models.UniqueConstraint(fields=["bidder", "version_no"], name="uq_financial_assessment_bidder_version"),
            models.UniqueConstraint(
                fields=["bidder"],
                condition=Q(used_in_consolidation=True),
                name="uq_single_financial_assessment_in_consolidation_per_bidder",
            ),
        ]
        indexes = [
            models.Index(fields=["process", "bidder", "status"]),
            models.Index(fields=["used_in_consolidation"]),
        ]

    def __str__(self):
        return f"{self.bidder} / fin-assessment v{self.version_no} / {self.result_code}"
