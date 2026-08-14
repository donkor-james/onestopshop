from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import TimeStampedUUIDModel
from apps.accounts.models import User
from apps.products.models import Product


class Review(TimeStampedUUIDModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    body = models.TextField(blank=True)
    # True if the user actually bought this product
    is_verified_purchase = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        # One review per user per product
        unique_together = ('product', 'user')
        indexes = [
            models.Index(fields=['product', 'rating'],
                         name='idx_review_product_rating'),
        ]

    def __str__(self):
        return f'{self.user.email} — {self.product.name} ({self.rating}★)'
