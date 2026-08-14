from django.db import models
from apps.core.models import TimeStampedUUIDModel
from .product import Product
from .variant import ProductVariant

from django.db import models
from apps.core.models import TimeStampedUUIDModel
from .variant import ProductVariant


class ProductImage(TimeStampedUUIDModel):
    # No more product FK — variant is now required, not nullable
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='products/')
    is_primary = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'
        ordering = ['order']
        indexes = [
            # Removed idx_image_product_primary — product FK is gone
            models.Index(
                fields=['variant', 'is_primary'],
                name='idx_image_variant_primary'
            ),
        ]

    def __str__(self):
        return f'Image for {self.variant.product.name} ({self.variant.size}/{self.variant.color})'

    def save(self, *args, **kwargs):
        # Simplified — no more two-scope logic
        if self.is_primary:
            ProductImage.objects.filter(
                variant=self.variant,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
