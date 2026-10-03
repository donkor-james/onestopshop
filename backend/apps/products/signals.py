from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from apps.products.models import Product, ProductVariant


@receiver([post_save, post_delete], sender=Product)
def bust_product_cache(sender, instance, **kwargs):
    cache.delete(f'product:{instance.slug}')

    try:
        keys = cache.keys('views.decorators.cache*')
        if keys:
            cache.delete_many(keys)
    except AttributeError:
        pass


@receiver([post_save, post_delete], sender=ProductVariant)
def bust_variant_cache(sender, instance, **kwargs):
    if instance.product:
        cache.delete(f'product:{instance.product.slug}')
