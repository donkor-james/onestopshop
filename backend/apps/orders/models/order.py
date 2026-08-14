from django.db import models
from apps.core.models import TimeStampedUUIDModel
from apps.accounts.models import User
from apps.discounts.models import DiscountCode
import uuid


def generate_order_reference():
    return f'ORD-{uuid.uuid4().hex[:8].upper()}'


class Order(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        PROCESSING = 'processing', 'Processing'
        SHIPPED = 'shipped', 'Shipped'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED = 'refunded', 'Refunded'

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,  # PROTECT — never delete a user with orders
        related_name='orders'
    )
    reference = models.CharField(
        max_length=20,
        unique=True,
        default=generate_order_reference
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    # Snapshot of address at time of order — address can change later
    shipping_address = models.JSONField()
    discount = models.ForeignKey(
        DiscountCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        indexes = [
            models.Index(fields=['reference'], name='idx_order_reference'),
            models.Index(fields=['user', 'status'],
                         name='idx_order_user_status'),
            models.Index(fields=['created_at'], name='idx_order_created'),
        ]

    def __str__(self):
        return f'Order {self.reference} — {self.user.email}'
