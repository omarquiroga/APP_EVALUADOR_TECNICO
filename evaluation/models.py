import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from common.choices import ConfidenceLevel, ResultCode, SubjectType, ValidationStatus
from common.mixins import AppendOnlyVersionMixin, TimeStampedMixin


class ValidationDecisionRecord(AppendOnlyVersionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey("procurement.ContractProcess", on_delete=models.PROTECT, related_name="validation_decisions")
    bidder = models.ForeignKey("bidders.Bidder", null=True, blank=True, on_delete=models.PROTECT, related_name="validation_decisions")
    module = models.CharField(max_length=50)
    subject_type = models.CharField(max_length=50, choices=SubjectType.choices)
    subject_uuid = models.UUIDField()
    rule_definition = models.ForeignKey("rules.RuleDefinition", on_delete=models.PROTECT, related_name="validation_decisions")
    rule_version = models.ForeignKey("rules.RuleVersion", on_delete=models.PROTECT, related_name="validation_decisions")
    normative_snapshot = models.ForeignKey(
        "normative.NormativeSnapshot", null=True, blank=True, on_delete=models.PROTECT, related_name="validation_decisions"
    )
    bidder_member = models.ForeignKey("bidders.BidderMember", null=True, blank=True, on_delete=models.PROTECT, related_name="validation_decisions")
    document = models.ForeignKey("documents.Document", null=True, blank=True, on_delete=models.PROTECT, related_name="validation_decisions")
    rup_record = models.ForeignKey("rup.RUPRecord", null=True, blank=True, on_delete=models.PROTECT, related_name="validation_decisions")
    rup_field_value = models.ForeignKey("rup.RUPFieldValue", null=True, blank=True, on_delete=models.PROTECT, related_name="validation_decisions")
    experience_record = models.ForeignKey(
        "experience.ExperienceRecord", null=True, blank=True, on_delete=models.PROTECT, related_name="validation_decisions"
    )
    experience_metric = models.ForeignKey(
        "experience.ExperienceMetric", null=True, blank=True, on_delete=models.PROTECT, related_name="validation_decisions"
    )
    financial_input_version = models.ForeignKey(
        "finance.FinancialInputVersion", null=True, blank=True, on_delete=models.PROTECT, related_name="validation_decisions"
    )
    external_check = models.ForeignKey(
        "external_checks.BidderMemberExternalCheck", null=True, blank=True, on_delete=models.PROTECT, related_name="validation_decisions"
    )
    input_payload = models.JSONField(default=dict)
    logic_trace = models.JSONField(default=dict)
    result_code = models.CharField(max_length=20, choices=ResultCode.choices, default=ResultCode.PENDING)
    result_value = models.JSONField(default=dict, blank=True)
    confidence_level = models.CharField(max_length=20, choices=ConfidenceLevel.choices, default=ConfidenceLevel.NOT_APPLICABLE)
    status = models.CharField(max_length=32, choices=ValidationStatus.choices, default=ValidationStatus.PRELIMINAR)
    human_required = models.BooleanField(default=True)
    human_confirmed_by = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="validation_decisions_confirmed"
    )
    human_confirmed_at = models.DateTimeField(null=True, blank=True)
    human_decision_note = models.TextField(blank=True)
    obsolete_reason = models.TextField(blank=True)
    reevaluation_required = models.BooleanField(default=False)

    SUBJECT_FIELD_MAP = {
        SubjectType.BIDDER: "bidder",
        SubjectType.BIDDER_MEMBER: "bidder_member",
        SubjectType.DOCUMENT: "document",
        SubjectType.RUP_RECORD: "rup_record",
        SubjectType.RUP_FIELD_VALUE: "rup_field_value",
        SubjectType.EXPERIENCE_RECORD: "experience_record",
        SubjectType.EXPERIENCE_METRIC: "experience_metric",
        SubjectType.FINANCIAL_INPUT_VERSION: "financial_input_version",
        SubjectType.EXTERNAL_CHECK: "external_check",
    }

    NON_BIDDER_SUBJECT_FIELDS = (
        "bidder_member",
        "document",
        "rup_record",
        "rup_field_value",
        "experience_record",
        "experience_metric",
        "financial_input_version",
        "external_check",
    )

    def clean(self):
        errors = {}
        expected_field = self.SUBJECT_FIELD_MAP.get(self.subject_type)
        if self.subject_type == SubjectType.BIDDER:
            populated_subject_fields = ["bidder"] if self.bidder_id else []
            if any(getattr(self, f"{field}_id", None) for field in self.NON_BIDDER_SUBJECT_FIELDS):
                errors["subject_type"] = "Cuando subject_type es 'bidder', no puede haber otra FK de sujeto poblada."
        else:
            populated_subject_fields = [field for field in self.NON_BIDDER_SUBJECT_FIELDS if getattr(self, f"{field}_id", None)]
        if not expected_field:
            errors["subject_type"] = "Tipo de sujeto no soportado."
        if not self.subject_uuid:
            errors["subject_uuid"] = "subject_uuid es obligatorio."
        if self.bidder_id and self.process_id and self.bidder.process_id != self.process_id:
            errors["bidder"] = "El proponente no pertenece al proceso indicado."
        if len(populated_subject_fields) != 1:
            errors["subject_type"] = "Debe existir exactamente una FK de sujeto poblada."
        elif expected_field not in populated_subject_fields:
            errors["subject_type"] = f"El subject_type '{self.subject_type}' no coincide con la FK poblada ({populated_subject_fields[0]})."
        if not errors and expected_field:
            subject_obj = getattr(self, expected_field, None)
            if subject_obj and getattr(subject_obj, "pk", None) != self.subject_uuid:
                errors["subject_uuid"] = "subject_uuid debe coincidir con la PK del sujeto referenciado."
            if subject_obj and hasattr(subject_obj, "process_id") and self.process_id and subject_obj.process_id != self.process_id:
                errors[expected_field] = "El sujeto evaluado no pertenece al proceso indicado."
        if self.bidder_member_id and self.bidder_id and self.bidder_member.bidder_id != self.bidder_id:
            errors["bidder_member"] = "El integrante no pertenece al proponente indicado."
        if self.rup_record_id and self.bidder_id and self.rup_record.bidder_id != self.bidder_id:
            errors["rup_record"] = "El registro RUP no pertenece al proponente indicado."
        if self.experience_record_id and self.bidder_id and self.experience_record.bidder_id != self.bidder_id:
            errors["experience_record"] = "El contrato de experiencia no pertenece al proponente indicado."
        if self.financial_input_version_id and self.bidder_id and self.financial_input_version.bidder_id != self.bidder_id:
            errors["financial_input_version"] = "El input financiero no pertenece al proponente indicado."
        if self.external_check_id and self.bidder_id and self.external_check.bidder_id != self.bidder_id:
            errors["external_check"] = "La consulta externa no pertenece al proponente indicado."
        if errors:
            raise ValidationError(errors)

    class Meta:
        db_table = "evaluation_validation_decision_record"
        verbose_name = "Registro de decision de validacion"
        verbose_name_plural = "Registros de decisiones de validacion"
        indexes = [
            models.Index(fields=["process", "module", "status"]),
            models.Index(fields=["subject_type", "subject_uuid"]),
            models.Index(fields=["bidder", "status"]),
            models.Index(fields=["rule_version", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    (
                        Q(subject_type=SubjectType.BIDDER, bidder_id__isnull=False)
                        & Q(bidder_member_id__isnull=True)
                        & Q(document_id__isnull=True)
                        & Q(rup_record_id__isnull=True)
                        & Q(rup_field_value_id__isnull=True)
                        & Q(experience_record_id__isnull=True)
                        & Q(experience_metric_id__isnull=True)
                        & Q(financial_input_version_id__isnull=True)
                        & Q(external_check_id__isnull=True)
                    )
                    | Q(subject_type=SubjectType.BIDDER_MEMBER, bidder_member_id__isnull=False)
                    | Q(subject_type=SubjectType.DOCUMENT, document_id__isnull=False)
                    | Q(subject_type=SubjectType.RUP_RECORD, rup_record_id__isnull=False)
                    | Q(subject_type=SubjectType.RUP_FIELD_VALUE, rup_field_value_id__isnull=False)
                    | Q(subject_type=SubjectType.EXPERIENCE_RECORD, experience_record_id__isnull=False)
                    | Q(subject_type=SubjectType.EXPERIENCE_METRIC, experience_metric_id__isnull=False)
                    | Q(subject_type=SubjectType.FINANCIAL_INPUT_VERSION, financial_input_version_id__isnull=False)
                    | Q(subject_type=SubjectType.EXTERNAL_CHECK, external_check_id__isnull=False)
                ),
                name="ck_validation_subject_fk_matches_type",
            ),
            models.CheckConstraint(
                condition=(
                    (
                        Q(subject_type=SubjectType.BIDDER)
                        & Q(bidder_id__isnull=False)
                        & Q(bidder_member_id__isnull=True)
                        & Q(document_id__isnull=True)
                        & Q(rup_record_id__isnull=True)
                        & Q(rup_field_value_id__isnull=True)
                        & Q(experience_record_id__isnull=True)
                        & Q(experience_metric_id__isnull=True)
                        & Q(financial_input_version_id__isnull=True)
                        & Q(external_check_id__isnull=True)
                    )
                    | (
                        Q(subject_type=SubjectType.BIDDER_MEMBER)
                        & Q(bidder_member_id__isnull=False)
                        & Q(document_id__isnull=True)
                        & Q(rup_record_id__isnull=True)
                        & Q(rup_field_value_id__isnull=True)
                        & Q(experience_record_id__isnull=True)
                        & Q(experience_metric_id__isnull=True)
                        & Q(financial_input_version_id__isnull=True)
                        & Q(external_check_id__isnull=True)
                    )
                    | (
                        Q(subject_type=SubjectType.DOCUMENT)
                        & Q(document_id__isnull=False)
                        & Q(bidder_member_id__isnull=True)
                        & Q(rup_record_id__isnull=True)
                        & Q(rup_field_value_id__isnull=True)
                        & Q(experience_record_id__isnull=True)
                        & Q(experience_metric_id__isnull=True)
                        & Q(financial_input_version_id__isnull=True)
                        & Q(external_check_id__isnull=True)
                    )
                    | (
                        Q(subject_type=SubjectType.RUP_RECORD)
                        & Q(rup_record_id__isnull=False)
                        & Q(bidder_member_id__isnull=True)
                        & Q(document_id__isnull=True)
                        & Q(rup_field_value_id__isnull=True)
                        & Q(experience_record_id__isnull=True)
                        & Q(experience_metric_id__isnull=True)
                        & Q(financial_input_version_id__isnull=True)
                        & Q(external_check_id__isnull=True)
                    )
                    | (
                        Q(subject_type=SubjectType.RUP_FIELD_VALUE)
                        & Q(rup_field_value_id__isnull=False)
                        & Q(bidder_member_id__isnull=True)
                        & Q(document_id__isnull=True)
                        & Q(rup_record_id__isnull=True)
                        & Q(experience_record_id__isnull=True)
                        & Q(experience_metric_id__isnull=True)
                        & Q(financial_input_version_id__isnull=True)
                        & Q(external_check_id__isnull=True)
                    )
                    | (
                        Q(subject_type=SubjectType.EXPERIENCE_RECORD)
                        & Q(experience_record_id__isnull=False)
                        & Q(bidder_member_id__isnull=True)
                        & Q(document_id__isnull=True)
                        & Q(rup_record_id__isnull=True)
                        & Q(rup_field_value_id__isnull=True)
                        & Q(experience_metric_id__isnull=True)
                        & Q(financial_input_version_id__isnull=True)
                        & Q(external_check_id__isnull=True)
                    )
                    | (
                        Q(subject_type=SubjectType.EXPERIENCE_METRIC)
                        & Q(experience_metric_id__isnull=False)
                        & Q(bidder_member_id__isnull=True)
                        & Q(document_id__isnull=True)
                        & Q(rup_record_id__isnull=True)
                        & Q(rup_field_value_id__isnull=True)
                        & Q(experience_record_id__isnull=True)
                        & Q(financial_input_version_id__isnull=True)
                        & Q(external_check_id__isnull=True)
                    )
                    | (
                        Q(subject_type=SubjectType.FINANCIAL_INPUT_VERSION)
                        & Q(financial_input_version_id__isnull=False)
                        & Q(bidder_member_id__isnull=True)
                        & Q(document_id__isnull=True)
                        & Q(rup_record_id__isnull=True)
                        & Q(rup_field_value_id__isnull=True)
                        & Q(experience_record_id__isnull=True)
                        & Q(experience_metric_id__isnull=True)
                        & Q(external_check_id__isnull=True)
                    )
                    | (
                        Q(subject_type=SubjectType.EXTERNAL_CHECK)
                        & Q(external_check_id__isnull=False)
                        & Q(bidder_member_id__isnull=True)
                        & Q(document_id__isnull=True)
                        & Q(rup_record_id__isnull=True)
                        & Q(rup_field_value_id__isnull=True)
                        & Q(experience_record_id__isnull=True)
                        & Q(experience_metric_id__isnull=True)
                        & Q(financial_input_version_id__isnull=True)
                    )
                ),
                name="ck_validation_exactly_one_subject_fk",
            ),
        ]

    def __str__(self):
        return f"{self.process.code} / {self.module} / {self.subject_type} / v{self.version_no}"


class ValidationEvidenceLink(TimeStampedMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    validation_decision = models.ForeignKey("evaluation.ValidationDecisionRecord", on_delete=models.CASCADE, related_name="evidence_links")
    document_version = models.ForeignKey("documents.DocumentVersion", on_delete=models.PROTECT, related_name="validation_evidence_links")
    document_page_ref = models.ForeignKey(
        "documents.DocumentPageRef", null=True, blank=True, on_delete=models.PROTECT, related_name="validation_evidence_links"
    )
    evidence_role = models.CharField(max_length=50, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        db_table = "evaluation_validation_evidence_link"
        verbose_name = "Vinculo de evidencia de validacion"
        verbose_name_plural = "Vinculos de evidencia de validacion"
        indexes = [models.Index(fields=["validation_decision", "document_version"])]

    def __str__(self):
        return f"{self.validation_decision} / {self.document_version}"
