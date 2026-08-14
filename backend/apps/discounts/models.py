from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import TimeStampedUUIDModel


class DiscountCode(TimeStampedUUIDModel):
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', 'Percentage'
        FIXED = 'fixed', 'Fixed Amount'

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE
    )
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    # If percentage, cap it at 100
    # Enforced in the serializer validate method
    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Minimum cart total required to use this code'
    )
    usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Leave blank for unlimited usage'
    )
    used_count = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Discount Code'
        verbose_name_plural = 'Discount Codes'
        indexes = [
            models.Index(fields=['code'], name='idx_discount_code'),
            models.Index(
                fields=['is_active', 'valid_from', 'valid_until'],
                name='idx_discount_active_validity'
            ),
        ]

    def __str__(self):
        return f'{self.code} ({self.discount_type} — {self.value})'

    @property
    def is_valid(self):
        from django.utils import timezone
        now = timezone.now()
        within_dates = self.valid_from <= now <= self.valid_until
        within_usage = self.usage_limit is None or self.used_count < self.usage_limit
        return self.is_active and within_dates and within_usage

    def apply_to(self, total):
        """Returns the discounted total"""
        if self.discount_type == self.DiscountType.PERCENTAGE:
            return total - (total * self.value / 100)
        return max(total - self.value, 0)
