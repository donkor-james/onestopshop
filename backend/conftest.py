import uuid
from unittest.mock import MagicMock, patch

import pytest
import factory
from django.core.cache import cache
from django.contrib.auth import get_user_model
from apps.products.models import Category, Product, ProductVariant
from apps.discounts.models import DiscountCode
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    email = factory.Sequence(lambda n: f'user{n}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')
    is_active = True


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category
    name = factory.Sequence(lambda n: f'Category {n}')


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product
    name = factory.Sequence(lambda n: f'Product {n}')
    base_price = '250.00'
    category = factory.SubFactory(CategoryFactory)
    is_active = True
    description = 'Test description'


class VariantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductVariant
    product = factory.SubFactory(ProductFactory)
    size = 'M'
    color = 'Red'
    sku = factory.Sequence(lambda n: f'SKU-{n}')
    stock_qty = 10
    price_override = '250.00'


class DiscountCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DiscountCode
    code = factory.Sequence(lambda n: f'SAVE{n}')
    discount_type = 'percentage'
    value = 10
    min_order_amount = 0
    usage_limit = 100
    used_count = 0
    valid_from = factory.LazyFunction(timezone.now)
    valid_until = factory.LazyFunction(
        lambda: timezone.now() + timedelta(days=30))
    is_active = True


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def make_variant(db):
    def _make(**kwargs):
        return VariantFactory(**kwargs)
    return _make


@pytest.fixture
def make_product(db):
    def _make(**kwargs):
        return ProductFactory(**kwargs)
    return _make


@pytest.fixture
def make_discount(db):
    def _make(**kwargs):
        return DiscountCodeFactory(**kwargs)
    return _make


@pytest.fixture(autouse=True)
def clear_cache():
    """cache_page / cart / discount caches must not leak between tests."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def paystack_ok():
    """Stub Paystack's initialize endpoint so tests never touch the network."""
    with patch('apps.orders.payments.requests.post') as post:
        response = MagicMock(status_code=200)
        response.json.return_value = {
            'status': True,
            'data': {'authorization_url': 'https://checkout.paystack.test/abc'},
        }
        post.return_value = response
        yield post


def idem_key():
    return {'HTTP_IDEMPOTENCY_KEY': str(uuid.uuid4())}
