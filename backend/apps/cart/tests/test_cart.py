import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from tests.factories import UserFactory, VariantFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client():
    client = APIClient()
    user = UserFactory()
    client.force_authenticate(user=user)
    return client, user


@pytest.mark.django_db
class TestCartView:
    def test_get_empty_cart(self, authenticated_client):
        client, user = authenticated_client
        response = client.get(reverse('cart'))
        assert response.status_code == 200
        assert response.data['item_count'] == 0
        assert response.data['items'] == []

    def test_unauthenticated_cannot_access_cart(self, api_client):
        response = api_client.get(reverse('cart'))
        assert response.status_code == 401


@pytest.mark.django_db
class TestCartItemAdd:
    def test_add_item_to_cart(self, authenticated_client):
        client, user = authenticated_client
        variant = VariantFactory(stock_qty=10, price_override='100.00')

        response = client.post(reverse('cart-add'), {
            'variant_id': str(variant.id),
            'quantity': 2
        }, format='json')

        assert response.status_code == 201
        assert response.data['quantity'] == 2
        assert response.data['product_name'] == variant.product.name

    def test_add_same_variant_increases_quantity(self, authenticated_client):
        client, user = authenticated_client
        variant = VariantFactory(stock_qty=10, price_override='100.00')

        # Add once
        client.post(reverse('cart-add'), {
            'variant_id': str(variant.id),
            'quantity': 1
        }, format='json')

        # Add again
        client.post(reverse('cart-add'), {
            'variant_id': str(variant.id),
            'quantity': 1
        }, format='json')

        # Get cart
        response = client.get(reverse('cart'))
        assert response.data['item_count'] == 1
        assert response.data['items'][0]['quantity'] == 2

    def test_cannot_exceed_stock(self, authenticated_client):
        client, user = authenticated_client
        variant = VariantFactory(stock_qty=5, price_override='100.00')

        response = client.post(reverse('cart-add'), {
            'variant_id': str(variant.id),
            'quantity': 10  # more than stock
        }, format='json')

        assert response.status_code == 400

    def test_cannot_add_out_of_stock_variant(self, authenticated_client):
        client, user = authenticated_client
        variant = VariantFactory(stock_qty=0, price_override='100.00')

        response = client.post(reverse('cart-add'), {
            'variant_id': str(variant.id),
            'quantity': 1
        }, format='json')

        assert response.status_code == 400


@pytest.mark.django_db
class TestCartClear:
    def test_clear_cart(self, authenticated_client):
        client, user = authenticated_client
        variant = VariantFactory(stock_qty=10, price_override='100.00')

        # Add item
        client.post(reverse('cart-add'), {
            'variant_id': str(variant.id),
            'quantity': 1
        }, format='json')

        # Clear cart
        response = client.delete(reverse('cart-clear'))
        assert response.status_code == 204

        # Confirm empty
        response = client.get(reverse('cart'))
        assert response.data['item_count'] == 0
