import uuid

from django.db import models

from common.mixins import TimeStampedMixin


class AuditEvent(TimeStampedMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey(
        "procurement.ContractProcess", null=True, blank=True, on_delete=models.PROTECT, related_name="audit_events"
    )
    bidder = models.ForeignKey("bidders.Bidder", null=True, blank=True, on_delete=models.PROTECT, related_name="audit_events")
    event_type = models.CharField(max_length=100)
    module = models.CharField(max_length=50)
    object_type = models.CharField(max_length=100)
    object_uuid = models.UUIDField()
    action = models.CharField(max_length=100)
    before_payload = models.JSONField(default=dict, blank=True)
    after_payload = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "audit_audit_event"
        verbose_name = "Evento de auditoria"
        verbose_name_plural = "Eventos de auditoria"
        indexes = [
            models.Index(fields=["process", "created_at"]),
            models.Index(fields=["object_type", "object_uuid"]),
            models.Index(fields=["module", "event_type"]),
        ]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} / {self.module} / {self.action}"
