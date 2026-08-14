from django.db import models
from apps.core.models import TimeStampedUUIDModel
from apps.accounts.models import User
from apps.products.models import ProductVariant


class Cart(TimeStampedUUIDModel):
    # One cart per user at all times
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart'
    )

    class Meta:
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'

    def __str__(self):
        return f'Cart — {self.user.email}'


class CartItem(TimeStampedUUIDModel):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        # A cart can't have the same variant twice — quantity is just updated
        unique_together = ('cart', 'variant')
        indexes = [
            models.Index(fields=['cart', 'variant'],
                         name='idx_cartitem_cart_variant'),
        ]

    def __str__(self):
        return f'{self.quantity}x {self.variant} in {self.cart}'

    @property
    def item_total(self):
        return self.variant.effective_price * self.quantity
