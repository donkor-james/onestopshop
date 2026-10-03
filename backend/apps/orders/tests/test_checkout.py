import pytest
from django.urls import reverse
from unittest.mock import patch
from apps.orders.models import Order
from apps.cart.models import Cart, CartItem
from apps.accounts.models import Address


def setup_cart(user, variant, quantity=1):
    cart, _ = Cart.objects.get_or_create(user=user)
    CartItem.objects.create(cart=cart, variant=variant, quantity=quantity)
    return cart


def create_address(user):
    return Address.objects.create(
        user=user,
        address_line1='12 Test Street',
        city='Accra',
        region='Greater Accra',
        country='Ghana',
        is_default=True
    )


@pytest.mark.django_db
class TestCheckout:
    @patch('apps.orders.views.send_order_confirmation_email.delay')
    def test_checkout_creates_order(self, mock_email, authenticated_client, make_variant):
        client, user = authenticated_client
        variant = make_variant(stock_qty=10, price_override='250.00')
        setup_cart(user, variant, quantity=1)
        address = create_address(user)

        response = client.post(reverse('checkout'), {
            'address_id': str(address.id)
        }, format='json')

        assert response.status_code == 201
        assert Order.objects.filter(user=user).count() == 1

    @patch('apps.orders.views.send_order_confirmation_email.delay')
    def test_checkout_deducts_stock(self, mock_email, authenticated_client, make_variant):
        client, user = authenticated_client
        variant = make_variant(stock_qty=10, price_override='250.00')
        setup_cart(user, variant, quantity=3)
        address = create_address(user)

        client.post(reverse('checkout'), {
            'address_id': str(address.id)
        }, format='json')

        variant.refresh_from_db()
        assert variant.stock_qty == 7

    @patch('apps.orders.views.send_order_confirmation_email.delay')
    def test_checkout_clears_cart(self, mock_email, authenticated_client, make_variant):
        client, user = authenticated_client
        variant = make_variant(stock_qty=10, price_override='250.00')
        setup_cart(user, variant, quantity=1)
        address = create_address(user)

        client.post(reverse('checkout'), {
            'address_id': str(address.id)
        }, format='json')

        cart = Cart.objects.get(user=user)
        assert cart.items.count() == 0

    def test_checkout_with_empty_cart_fails(self, authenticated_client):
        client, user = authenticated_client
        address = create_address(user)

        response = client.post(reverse('checkout'), {
            'address_id': str(address.id)
        }, format='json')

        assert response.status_code == 400

    def test_checkout_prevents_overselling(self, authenticated_client, make_variant):
        client, user = authenticated_client
        variant = make_variant(stock_qty=2, price_override='250.00')
        setup_cart(user, variant, quantity=5)
        address = create_address(user)

        response = client.post(reverse('checkout'), {
            'address_id': str(address.id)
        }, format='json')

        assert response.status_code == 400
        variant.refresh_from_db()
        assert variant.stock_qty == 2
