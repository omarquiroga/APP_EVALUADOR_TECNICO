import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from common.choices import RuleType, SeverityLevel
from common.mixins import AppendOnlyVersionMixin, EditableMixin, TimeStampedMixin


class RuleDefinition(TimeStampedMixin, EditableMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    module = models.CharField(max_length=50)
    rule_type = models.CharField(max_length=32, choices=RuleType.choices)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    default_human_required = models.BooleanField(default=True)

    class Meta:
        db_table = "rules_rule_definition"
        verbose_name = "Definicion de regla"
        verbose_name_plural = "Definiciones de reglas"
        indexes = [models.Index(fields=["module", "rule_type"])]


class RuleVersion(AppendOnlyVersionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule_definition = models.ForeignKey("rules.RuleDefinition", on_delete=models.CASCADE, related_name="versions")
    normative_snapshot = models.ForeignKey(
        "normative.NormativeSnapshot", null=True, blank=True, on_delete=models.PROTECT, related_name="rule_versions"
    )
    process = models.ForeignKey(
        "procurement.ContractProcess", null=True, blank=True, on_delete=models.PROTECT, related_name="rule_versions"
    )
    version_label = models.CharField(max_length=50)
    parameters = models.JSONField(default=dict)
    severity = models.CharField(max_length=16, choices=SeverityLevel.choices, default=SeverityLevel.MEDIUM)
    is_subsanable = models.BooleanField(default=False)
    human_required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    checksum = models.CharField(max_length=128)

    class Meta:
        db_table = "rules_rule_version"
        verbose_name = "Version de regla"
        verbose_name_plural = "Versiones de reglas"
        constraints = [
            models.UniqueConstraint(
                fields=["rule_definition", "version_no", "process"],
                name="uq_rule_version_process_number",
            )
        ]
        indexes = [
            models.Index(fields=["process", "is_active"]),
            models.Index(fields=["rule_definition", "is_active"]),
        ]


class ProcessRuleActivation(TimeStampedMixin, EditableMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey("procurement.ContractProcess", on_delete=models.CASCADE, related_name="rule_activations")
    rule_definition = models.ForeignKey("rules.RuleDefinition", on_delete=models.PROTECT, related_name="process_activations")
    rule_version = models.ForeignKey("rules.RuleVersion", on_delete=models.PROTECT, related_name="activations")
    is_active = models.BooleanField(default=True)
    activation_notes = models.TextField(blank=True)

    def clean(self):
        errors = {}
        if self.rule_version_id and self.rule_definition_id:
            if self.rule_version.rule_definition_id != self.rule_definition_id:
                errors["rule_definition"] = "rule_definition debe coincidir con rule_version.rule_definition."
            if self.rule_version.process_id and self.rule_version.process_id != self.process_id:
                errors["rule_version"] = "La version de regla pertenece a otro proceso."
        if errors:
            raise ValidationError(errors)

    class Meta:
        db_table = "rules_process_rule_activation"
        verbose_name = "Activacion de regla del proceso"
        verbose_name_plural = "Activaciones de reglas del proceso"
        constraints = [
            models.UniqueConstraint(fields=["process", "rule_version"], name="uq_process_rule_activation"),
            models.UniqueConstraint(
                fields=["process", "rule_definition"],
                condition=Q(is_active=True),
                name="uq_active_rule_definition_per_process",
            ),
        ]
        indexes = [models.Index(fields=["process", "is_active"])]
