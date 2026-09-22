from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache
from apps.discounts.models import DiscountCode


@receiver(post_save, sender=DiscountCode)
def bust_discount_cache(sender, instance, **kwargs):
    """
    Bust the discount code cache when it's updated —
    e.g. deactivated, usage limit reached, or value changed.
    """
    cache.delete(f'discount:{instance.code.upper()}')
