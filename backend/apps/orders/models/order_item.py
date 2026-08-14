from django.db import models
from django.core.validators import MinValueValidator
from apps.core.models import TimeStampedUUIDModel
from apps.products.models import ProductVariant
from .order import Order


class OrderItem(TimeStampedUUIDModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    # SET_NULL so order history isn't lost if a variant is deleted
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True,
        related_name='order_items'
    )
    quantity = models.PositiveIntegerField()
    # Price is snapshotted at purchase — never changes even if product price changes
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    def __str__(self):
        return f'{self.quantity}x {self.variant} in {self.order.reference}'

    @property
    def subtotal(self):
        return self.unit_price * self.quantity
