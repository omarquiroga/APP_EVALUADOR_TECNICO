import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from common.choices import BidderState
from common.mixins import EditableMixin, TimeStampedMixin


class Bidder(TimeStampedMixin, EditableMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey("procurement.ContractProcess", on_delete=models.CASCADE, related_name="bidders")
    name = models.CharField(max_length=255)
    identification_type = models.CharField(max_length=30)
    identification_number = models.CharField(max_length=50)
    bidder_type = models.CharField(max_length=30)
    state = models.CharField(max_length=32, choices=BidderState.choices, default=BidderState.REGISTERED)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "bidders_bidder"
        verbose_name = "Proponente"
        verbose_name_plural = "Proponentes"
        constraints = [
            models.UniqueConstraint(
                fields=["process", "identification_type", "identification_number"],
                name="uq_bidder_process_identification",
            )
        ]
        indexes = [
            models.Index(fields=["process", "state"]),
            models.Index(fields=["identification_number"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.identification_number})"


class BidderMember(TimeStampedMixin, EditableMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bidder = models.ForeignKey("bidders.Bidder", on_delete=models.CASCADE, related_name="members")
    name = models.CharField(max_length=255)
    identification_type = models.CharField(max_length=30)
    identification_number = models.CharField(max_length=50)
    member_role = models.CharField(max_length=50, blank=True)
    participation_percentage = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    is_lead = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "bidders_bidder_member"
        verbose_name = "Integrante del proponente"
        verbose_name_plural = "Integrantes del proponente"
        constraints = [
            models.UniqueConstraint(
                fields=["bidder", "identification_type", "identification_number"],
                name="uq_bidder_member_identification",
            )
        ]
        indexes = [models.Index(fields=["bidder", "is_lead"])]

    def __str__(self):
        return f"{self.name} ({self.identification_number})"
