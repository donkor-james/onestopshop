from django.db import models
from django.utils.text import slugify
from apps.core.models import TimeStampedUUIDModel
from .category import Category


class ProductQuerySet(models.QuerySet):
    def available(self):
        return self.filter(is_active=True, variants__stock_qty__gt=0).distinct()

    def by_category(self, slug):
        return self.filter(category__slug=slug)


class ProductManager(models.Manager):
    def get_queryset(self):
        return ProductQuerySet(self.model, using=self._db)

    def available(self):
        return self.get_queryset().available()

    def by_category(self, slug):
        return self.get_queryset().by_category(slug)


class Product(TimeStampedUUIDModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products'
    )
    is_active = models.BooleanField(default=True)

    objects = ProductManager()

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        indexes = [
            # Already short
            models.Index(fields=['slug'], name='idx_prod_slug'),
            models.Index(fields=['is_active'],
                         name='idx_prod_active'),  # Already short
            # Composite index — used by filtered product listings
            models.Index(
                fields=['category', 'is_active', 'base_price'],
                name='idx_prod_cat_act_pri'  # Shortened name
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
