from django.db import models
from apps.core.models import TimeStampedUUIDModel
from .order import Order


class OrderEvent(TimeStampedUUIDModel):
    """
    An immutable audit log of every status change on an order.
    Never updated or deleted — only appended to.
    Useful for customer support and order tracking.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='events'
    )
    status = models.CharField(max_length=20, choices=Order.Status.choices)
    note = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Order Event'
        verbose_name_plural = 'Order Events'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.order.reference} → {self.status}'
