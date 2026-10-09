from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedUUIDModel


class IdempotencyKey(TimeStampedUUIDModel):
    """
    One row per (user, endpoint, Idempotency-Key). The unique constraint is the
    mutex: only one request can ever claim a given key, so a retry or a
    double-click always results in the same response.
    """

    class State(models.TextChoices):
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='idempotency_keys')
    key = models.CharField(max_length=128)
    endpoint = models.CharField(max_length=200)
    request_hash = models.CharField(max_length=64)
    state = models.CharField(
        max_length=12, choices=State.choices, default=State.PROCESSING)
    response_status = models.PositiveSmallIntegerField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'endpoint', 'key'],
                name='uniq_idem_user_endpoint_key'),
        ]
        indexes = [models.Index(fields=['created_at'],
                                name='idx_idem_created')]
