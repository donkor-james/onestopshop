from django.db import models
from django.core.validators import MinValueValidator
from apps.core.models import TimeStampedUUIDModel
from .product import Product


class ProductVariant(TimeStampedUUIDModel):
    """
    A variant is a specific combination of size and color for a product.
    Each variant has its own stock and can optionally override the base price.
    e.g. Red Dress in Size M at GHS 250
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants'
    )
    # S, M, L, XL or 38, 39, 40
    size = models.CharField(max_length=20, blank=True)
    color = models.CharField(max_length=50, blank=True)
    sku = models.CharField(max_length=100, unique=True)  # Stock Keeping Unit
    stock_qty = models.PositiveIntegerField(default=0)
    # If null, the product's base_price is used
    price_override = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )

    class Meta:
        verbose_name = 'Product Variant'
        verbose_name_plural = 'Product Variants'
        # A product can't have two variants with the same size and color
        unique_together = ('product', 'size', 'color')
        indexes = [
            models.Index(fields=['sku'], name='idx_variant_sku'),
            models.Index(fields=['product', 'stock_qty'],
                         name='idx_variant_product_stock'),
        ]

    def __str__(self):
        return f'{self.product.name} — {self.size} / {self.color}'

    @property
    def effective_price(self):
        """Returns the actual price — override if set, else product base price"""
        return self.price_override if self.price_override else self.product.base_price

    @property
    def is_in_stock(self):
        return self.stock_qty > 0
