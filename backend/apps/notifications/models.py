from django.db import models
from apps.core.models import TimeStampedUUIDModel
from apps.accounts.models import User


class Notification(TimeStampedUUIDModel):
    class NotificationType(models.TextChoices):
        ORDER_CONFIRMED = 'order_confirmed', 'Order Confirmed'
        ORDER_SHIPPED = 'order_shipped', 'Order Shipped'
        ORDER_DELIVERED = 'order_delivered', 'Order Delivered'
        ORDER_CANCELLED = 'order_cancelled', 'Order Cancelled'
        PROMO = 'promo', 'Promotion'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    # Link to the relevant order if applicable
    order_reference = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read'],
                         name='idx_notification_user_read'),
            models.Index(fields=['created_at'],
                         name='idx_notification_created'),
        ]

    def __str__(self):
        return f'{self.notification_type} — {self.user.email}'
