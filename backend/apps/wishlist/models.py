from django.db import models
from apps.core.models import TimeStampedUUIDModel
from apps.accounts.models import User
from apps.products.models import Product


class Wishlist(models.Model):
    # One wishlist per user
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='wishlist'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Wishlist'
        verbose_name_plural = 'Wishlists'

    def __str__(self):
        return f'Wishlist — {self.user.email}'


class WishlistItem(TimeStampedUUIDModel):
    wishlist = models.ForeignKey(
        Wishlist,
        on_delete=models.CASCADE,
        related_name='items'
    )
    # Wishlist saves products not variants — customer hasn't picked size/color yet
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='wishlist_items'
    )

    class Meta:
        verbose_name = 'Wishlist Item'
        verbose_name_plural = 'Wishlist Items'
        # A product can only appear once per wishlist
        unique_together = ('wishlist', 'product')
        indexes = [
            models.Index(
                fields=['wishlist', 'product'],
                name='idx_wishlist_item'
            )
        ]

    def __str__(self):
        return f'{self.product.name} in {self.wishlist.user.email} wishlist'
