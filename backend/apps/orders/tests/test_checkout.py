import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from tests.factories import (
    UserFactory, VariantFactory, DiscountCodeFactory
)
from apps.users.models import Address
from apps.orders.models import Order
from apps.cart.models import Cart, CartItem
from unittest.mock import patch


@pytest.fixture
def authenticated_client():
    client = APIClient()
    user = UserFactory()
    client.force_authenticate(user=user)
    return client, user


def setup_cart_with_item(user, variant, quantity=1):
    """Helper to add an item to a user's cart"""
    cart, _ = Cart.objects.get_or_create(user=user)
    CartItem.objects.create(cart=cart, variant=variant, quantity=quantity)
    return cart


def create_address(user):
    """Helper to create a default address for a user"""
    return Address.objects.create(
        user=user,
        street='12 Test Street',
        city='Accra',
        region='Greater Accra',
        country='Ghana',
        is_default=True
    )


@pytest.mark.django_db
class TestCheckout:
    @patch('apps.orders.views.send_order_confirmation_email.delay')
    def test_checkout_creates_order(self, mock_email, authenticated_client):
        client, user = authenticated_client
        variant = VariantFactory(stock_qty=10, price_override='250.00')
        setup_cart_with_item(user, variant, quantity=2)
        address = create_address(user)

        response = client.post(reverse('checkout'), {
            'address_id': str(address.id)
        }, format='json')

        assert response.status_code == 201
        assert response.data['status'] == 'pending'
        assert Order.objects.filter(user=user).count() == 1

    @patch('apps.orders.views.send_order_confirmation_email.delay')
    def test_checkout_deducts_stock(self, mock_email, authenticated_client):
        client, user = authenticated_client
        variant = VariantFactory(stock_qty=10, price_override='250.00')
        setup_cart_with_item(user, variant, quantity=3)
        address = create_address(user)

        client.post(reverse('checkout'), {
            'address_id': str(address.id)
        }, format='json')

        variant.refresh_from_db()
        assert variant.stock_qty == 7  # 10 - 3

    @patch('apps.orders.views.send_order_confirmation_email.delay')
    def test_checkout_clears_cart(self, mock_email, authenticated_client):
        client, user = authenticated_client
        variant = VariantFactory(stock_qty=10, price_override='250.00')
        setup_cart_with_item(user, variant, quantity=1)
        address = create_address(user)

        client.post(reverse('checkout'), {
            'address_id': str(address.id)
        }, format='json')

        cart = Cart.objects.get(user=user)
        assert cart.items.count() == 0

    @patch('apps.orders.views.send_order_confirmation_email.delay')
    def test_checkout_fires_email_task(self, mock_email, authenticated_client):
        client, user = authenticated_client
        variant = VariantFactory(stock_qty=10, price_override='250.00')
        setup_cart_with_item(user, variant, quantity=1)
        address = create_address(user)

        client.post(reverse('checkout'), {
            'address_id': str(address.id)
        }, format='json')

        # Confirm email task was called
        mock_email.assert_called_once()

    def test_checkout_with_empty_cart_fails(self, authenticated_client):
        client, user = authenticated_client
        address = create_address(user)

        response = client.post(reverse('checkout'), {
            'address_id': str(address.id)
        }, format='json')

        assert response.status_code == 400
        assert 'empty' in response.data['error'].lower()

    @patch('apps.orders.views.send_order_confirmation_email.delay')
    def test_checkout_with_discount(self, mock_email, authenticated_client):
        client, user = authenticated_client
        variant = VariantFactory(stock_qty=10, price_override='500.00')
        setup_cart_with_item(user, variant, quantity=1)
        address = create_address(user)
        discount = DiscountCodeFactory(
            code='SAVE20',
            discount_type='percentage',
            value=20
        )

        response = client.post(reverse('checkout'), {
            'address_id': str(address.id),
            'discount_code': 'SAVE20'
        }, format='json')

        assert response.status_code == 201
        # 500 - 20% = 400
        assert float(response.data['total_amount']) == 400.00

    @patch('apps.orders.views.send_order_confirmation_email.delay')
    def test_checkout_prevents_overselling(self, mock_email, authenticated_client):
        client, user = authenticated_client
        # Only 2 in stock
        variant = VariantFactory(stock_qty=2, price_override='250.00')
        # But cart has 5
        setup_cart_with_item(user, variant, quantity=5)
        address = create_address(user)

        response = client.post(reverse('checkout'), {
            'address_id': str(address.id)
        }, format='json')

        assert response.status_code == 400
        # Stock should not have changed
        variant.refresh_from_db()
        assert variant.stock_qty == 2

    def test_checkout_with_invalid_address_fails(self, authenticated_client):
        client, user = authenticated_client
        variant = VariantFactory(stock_qty=10, price_override='250.00')
        setup_cart_with_item(user, variant, quantity=1)

        response = client.post(reverse('checkout'), {
            'address_id': '00000000-0000-0000-0000-000000000000'
        }, format='json')

        assert response.status_code == 400
