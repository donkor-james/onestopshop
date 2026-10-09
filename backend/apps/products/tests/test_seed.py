import pytest
from django.core.management import call_command

from apps.products.models import Product, ProductVariant


@pytest.mark.django_db
def test_seed_products_creates_unique_products_and_variants():
    call_command('seed_products', products=50, variants=2, batch=20)
    assert Product.objects.count() == 50
    assert ProductVariant.objects.count() == 100
    assert len(set(Product.objects.values_list('slug', flat=True))) == 50
