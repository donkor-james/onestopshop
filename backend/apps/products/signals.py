from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from apps.products.models import Product, ProductVariant


@receiver([post_save, post_delete], sender=Product)
def bust_product_cache(sender, instance, **kwargs):
    """
    Bust the product detail cache when a product is saved or deleted.
    Also bust the listing cache since the product appears there too.
    """
    # Bust product detail cache
    cache.delete(f'product:{instance.slug}')

    # Bust the whole listing cache — easier than tracking individual pages
    cache.delete_many(cache.keys('views.decorators.cache*') or [])


@receiver([post_save, post_delete], sender=ProductVariant)
def bust_variant_cache(sender, instance, **kwargs):
    """
    Bust the parent product cache when a variant changes —
    stock levels and prices shown in product detail come from variants.
    """
    if instance.product:
        cache.delete(f'product:{instance.product.slug}')
