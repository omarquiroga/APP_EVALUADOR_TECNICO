import uuid

from django.core.exceptions import ValidationError
from django.db import models

from common.choices import CauseStatus, SeverityLevel
from common.mixins import AppendOnlyVersionMixin, EditableMixin, TimeStampedMixin


class RejectionCauseDefinition(TimeStampedMixin, EditableMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey("procurement.ContractProcess", on_delete=models.CASCADE, related_name="rejection_cause_definitions")
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_subsanable = models.BooleanField(default=False)
    severity = models.CharField(max_length=16, choices=SeverityLevel.choices, default=SeverityLevel.HIGH)
    human_required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "causals_rejection_cause_definition"
        verbose_name = "Definicion de causal de rechazo"
        verbose_name_plural = "Definiciones de causales de rechazo"
        constraints = [
            models.UniqueConstraint(
                fields=["process", "code"], name="uq_rejection_cause_definition_process_code"
            )
        ]
        indexes = [models.Index(fields=["process", "is_active"])]

    def __str__(self):
        return f"{self.code} - {self.name}"


class RejectionCauseAssessment(AppendOnlyVersionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey("procurement.ContractProcess", on_delete=models.PROTECT, related_name="rejection_cause_assessments")
    bidder = models.ForeignKey("bidders.Bidder", on_delete=models.PROTECT, related_name="rejection_cause_assessments")
    cause_definition = models.ForeignKey("causals.RejectionCauseDefinition", on_delete=models.PROTECT, related_name="assessments")
    triggering_decision_record = models.ForeignKey(
        "evaluation.ValidationDecisionRecord",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="triggered_rejection_causes",
    )
    status = models.CharField(max_length=20, choices=CauseStatus.choices, default=CauseStatus.NOT_TRIGGERED)
    origin_type = models.CharField(max_length=20, default="mixed")
    is_subsanable = models.BooleanField(default=False)
    evidence_summary = models.TextField(blank=True)
    human_review_required = models.BooleanField(default=True)
    reviewed_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rejection_cause_assessments_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)
    impact_on_closure = models.BooleanField(default=False)
    impact_on_final_status = models.CharField(max_length=20, blank=True)

    def clean(self):
        errors = {}

        if self.cause_definition_id and self.cause_definition.process_id != self.process_id:
            errors["cause_definition"] = "La definicion de causal pertenece a otro proceso."

        if self.bidder_id and self.bidder.process_id != self.process_id:
            errors["bidder"] = "El proponente no pertenece al proceso indicado."

        if self.triggering_decision_record_id:
            if self.triggering_decision_record.process_id != self.process_id:
                errors["triggering_decision_record"] = "La validacion origen pertenece a otro proceso."
            if self.triggering_decision_record.bidder_id and self.triggering_decision_record.bidder_id != self.bidder_id:
                errors["triggering_decision_record"] = "La validacion origen pertenece a otro proponente."

        if errors:
            raise ValidationError(errors)

    class Meta:
        db_table = "causals_rejection_cause_assessment"
        verbose_name = "Evaluacion de causal de rechazo"
        verbose_name_plural = "Evaluaciones de causales de rechazo"
        indexes = [
            models.Index(fields=["process", "bidder", "status"]),
            models.Index(fields=["impact_on_closure"]),
        ]

    def __str__(self):
        return f"{self.bidder} / {self.cause_definition.code} / {self.status}"
