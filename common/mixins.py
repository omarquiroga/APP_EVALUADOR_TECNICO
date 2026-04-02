from django.conf import settings
from django.db import models


User = settings.AUTH_USER_MODEL


class TimeStampedMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_created",
    )

    class Meta:
        abstract = True


class EditableMixin(models.Model):
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_updated",
    )
    row_version = models.PositiveIntegerField(default=1)

    class Meta:
        abstract = True


class AppendOnlyVersionMixin(TimeStampedMixin):
    version_no = models.PositiveIntegerField(default=1)
    supersedes = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="superseded_by_set",
    )

    class Meta:
        abstract = True
