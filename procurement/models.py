import uuid

from django.conf import settings
from django.db import models

from common.choices import ProcessState
from common.mixins import EditableMixin, TimeStampedMixin


User = settings.AUTH_USER_MODEL


class ContractProcess(TimeStampedMixin, EditableMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    entity_name = models.CharField(max_length=255)
    process_type = models.CharField(max_length=100)
    modality = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    reference_number = models.CharField(max_length=100, blank=True)
    opening_date = models.DateField(null=True, blank=True)
    closing_date = models.DateField(null=True, blank=True)
    state = models.CharField(max_length=32, choices=ProcessState.choices, default=ProcessState.DRAFT)
    current_rule_bundle_version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "procurement_contract_process"
        verbose_name = "Proceso de contratacion"
        verbose_name_plural = "Procesos de contratacion"
        indexes = [
            models.Index(fields=["state", "modality"]),
            models.Index(fields=["opening_date", "closing_date"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class ProcessTeamMember(TimeStampedMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey("procurement.ContractProcess", on_delete=models.CASCADE, related_name="team_members")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="process_assignments")
    role_code = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "procurement_process_team_member"
        verbose_name = "Integrante del equipo del proceso"
        verbose_name_plural = "Integrantes del equipo del proceso"
        constraints = [
            models.UniqueConstraint(fields=["process", "user", "role_code"], name="uq_process_team_member_role")
        ]

    def __str__(self):
        return f"{self.process.code} / {self.user} / {self.role_code}"
