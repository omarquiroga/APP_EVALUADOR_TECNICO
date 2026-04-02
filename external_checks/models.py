import uuid

from django.db import models

from common.choices import CheckStatus
from common.mixins import AppendOnlyVersionMixin, EditableMixin, TimeStampedMixin


class ExternalCheckSource(TimeStampedMixin, EditableMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    homepage_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "external_checks_source"
        verbose_name = "Fuente de consulta externa"
        verbose_name_plural = "Fuentes de consultas externas"


class BidderMemberExternalCheck(AppendOnlyVersionMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey("procurement.ContractProcess", on_delete=models.CASCADE, related_name="external_checks")
    bidder = models.ForeignKey("bidders.Bidder", on_delete=models.CASCADE, related_name="external_checks")
    bidder_member = models.ForeignKey("bidders.BidderMember", on_delete=models.CASCADE, related_name="external_checks")
    source = models.ForeignKey("external_checks.ExternalCheckSource", on_delete=models.PROTECT, related_name="checks")
    query_type = models.CharField(max_length=50)
    query_value = models.CharField(max_length=255)
    result_status = models.CharField(max_length=20, choices=CheckStatus.choices, default=CheckStatus.NOT_RUN)
    raw_result_payload = models.JSONField(default=dict, blank=True)
    evidence_document = models.ForeignKey(
        "documents.DocumentVersion", null=True, blank=True, on_delete=models.PROTECT, related_name="external_checks"
    )
    consulted_at = models.DateTimeField(null=True, blank=True)
    requires_human_review = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "external_checks_bidder_member_check"
        verbose_name = "Consulta externa de integrante"
        verbose_name_plural = "Consultas externas de integrantes"
        indexes = [
            models.Index(fields=["process", "bidder", "result_status"]),
            models.Index(fields=["bidder_member", "source"]),
        ]
