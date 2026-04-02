import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from common.choices import ScopeType, ValidationStatus
from common.mixins import AppendOnlyVersionMixin, EditableMixin, TimeStampedMixin


class ExperienceRecord(AppendOnlyVersionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey("procurement.ContractProcess", on_delete=models.PROTECT, related_name="experience_records")
    bidder = models.ForeignKey("bidders.Bidder", on_delete=models.PROTECT, related_name="experience_records")
    bidder_member = models.ForeignKey(
        "bidders.BidderMember", null=True, blank=True, on_delete=models.PROTECT, related_name="experience_records"
    )
    contract_identifier = models.CharField(max_length=100)
    contract_type = models.CharField(max_length=100)
    contract_object = models.TextField()
    contractor_role = models.CharField(max_length=50, blank=True)
    contract_value_nominal = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    contract_currency = models.CharField(max_length=10, default="COP")
    contract_year = models.PositiveIntegerField(null=True, blank=True)
    execution_start_date = models.DateField(null=True, blank=True)
    execution_end_date = models.DateField(null=True, blank=True)
    execution_length_value = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    execution_length_unit = models.CharField(max_length=30, blank=True)
    participation_percentage = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    is_general_experience_candidate = models.BooleanField(default=True)
    is_specific_experience_candidate = models.BooleanField(default=False)
    source_document = models.ForeignKey(
        "documents.DocumentVersion", null=True, blank=True, on_delete=models.PROTECT, related_name="experience_records"
    )
    review_status = models.CharField(max_length=32, choices=ValidationStatus.choices, default=ValidationStatus.NOT_EVALUATED)

    class Meta:
        db_table = "experience_experience_record"
        verbose_name = "Contrato de experiencia"
        verbose_name_plural = "Contratos de experiencia"
        indexes = [
            models.Index(fields=["bidder", "contract_identifier"]),
            models.Index(fields=["process", "bidder_member"]),
        ]

    def __str__(self):
        return f"{self.contract_identifier} / {self.bidder} / v{self.version_no}"


class ExperienceMetric(AppendOnlyVersionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    experience_record = models.ForeignKey("experience.ExperienceRecord", on_delete=models.CASCADE, related_name="metrics")
    metric_code = models.CharField(max_length=100)
    metric_value_number = models.DecimalField(max_digits=20, decimal_places=4)
    metric_unit = models.CharField(max_length=30)
    source = models.CharField(max_length=30)
    calculation_trace = models.JSONField(default=dict, blank=True)
    document_page_ref = models.ForeignKey(
        "documents.DocumentPageRef", null=True, blank=True, on_delete=models.PROTECT, related_name="experience_metrics"
    )

    class Meta:
        db_table = "experience_experience_metric"
        verbose_name = "Metrica de experiencia"
        verbose_name_plural = "Metricas de experiencia"
        indexes = [models.Index(fields=["experience_record", "metric_code"])]

    def __str__(self):
        return f"{self.experience_record.contract_identifier} / {self.metric_code} / v{self.version_no}"


class MinimumWageYear(TimeStampedMixin, EditableMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    year = models.PositiveIntegerField(unique=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "experience_minimum_wage_year"
        verbose_name = "SMMLV por ano"
        verbose_name_plural = "SMMLV por ano"

    def __str__(self):
        return f"{self.year} - {self.amount}"


class SMMLVConversionRecord(AppendOnlyVersionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    experience_record = models.ForeignKey("experience.ExperienceRecord", on_delete=models.CASCADE, related_name="smmlv_conversions")
    minimum_wage_year = models.ForeignKey("experience.MinimumWageYear", on_delete=models.PROTECT, related_name="conversions")
    source_value = models.DecimalField(max_digits=20, decimal_places=2)
    resulting_smmlv = models.DecimalField(max_digits=20, decimal_places=4)
    calculation_trace = models.JSONField(default=dict)

    class Meta:
        db_table = "experience_smmlv_conversion_record"
        verbose_name = "Conversion a SMMLV"
        verbose_name_plural = "Conversiones a SMMLV"
        indexes = [models.Index(fields=["experience_record", "minimum_wage_year"])]

    def __str__(self):
        return f"{self.experience_record.contract_identifier} / {self.resulting_smmlv} SMMLV"


class ExperienceAssessment(AppendOnlyVersionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey("procurement.ContractProcess", on_delete=models.PROTECT, related_name="experience_assessments")
    bidder = models.ForeignKey("bidders.Bidder", on_delete=models.PROTECT, related_name="experience_assessments")
    experience_record = models.ForeignKey("experience.ExperienceRecord", on_delete=models.PROTECT, related_name="assessments")
    rule_definition = models.ForeignKey("rules.RuleDefinition", on_delete=models.PROTECT, related_name="experience_assessments")
    rule_version = models.ForeignKey("rules.RuleVersion", on_delete=models.PROTECT, related_name="experience_assessments")
    scope = models.CharField(max_length=16, choices=ScopeType.choices)
    is_valid = models.BooleanField(default=False)
    rejection_reason_code = models.CharField(max_length=100, blank=True)
    accepted_contribution_value = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    accepted_contribution_unit = models.CharField(max_length=30, blank=True)

    class Meta:
        db_table = "experience_experience_assessment"
        verbose_name = "Evaluacion de experiencia"
        verbose_name_plural = "Evaluaciones de experiencia"
        indexes = [
            models.Index(fields=["bidder", "scope", "is_valid"]),
            models.Index(fields=["experience_record", "scope"]),
        ]

    def __str__(self):
        return f"{self.experience_record.contract_identifier} / {self.scope} / {'valido' if self.is_valid else 'no valido'}"


class ExperienceConsolidation(AppendOnlyVersionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey("procurement.ContractProcess", on_delete=models.PROTECT, related_name="experience_consolidations")
    bidder = models.ForeignKey("bidders.Bidder", on_delete=models.PROTECT, related_name="experience_consolidations")
    scope = models.CharField(max_length=16, choices=ScopeType.choices)
    total_valid_contracts = models.PositiveIntegerField(default=0)
    total_accepted_value = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    total_accepted_smmlv = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    meets_requirement = models.BooleanField(default=False)
    consolidation_trace = models.JSONField(default=dict)
    status = models.CharField(max_length=32, choices=ValidationStatus.choices, default=ValidationStatus.PRELIMINAR)

    class Meta:
        db_table = "experience_experience_consolidation"
        verbose_name = "Consolidacion de experiencia"
        verbose_name_plural = "Consolidaciones de experiencia"
        indexes = [models.Index(fields=["process", "bidder", "scope"])]

    def __str__(self):
        return f"{self.bidder} / {self.scope} / v{self.version_no}"
