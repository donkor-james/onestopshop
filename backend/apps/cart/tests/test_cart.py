import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestCartView:
    def test_get_empty_cart(self, authenticated_client):
        client, user = authenticated_client
        response = client.get(reverse('cart'))
        assert response.status_code == 200
        print(response.data)
        assert response.data['items'] == []

    def test_unauthenticated_cannot_access_cart(self, api_client):
        response = api_client.get(reverse('cart'))
        assert response.status_code == 401


@pytest.mark.django_db
class TestCartItemAdd:
    def test_add_item_to_cart(self, authenticated_client, make_variant):
        client, user = authenticated_client
        variant = make_variant(stock_qty=10, price_override='100.00')

        response = client.post(reverse('cart-item-create'), {
            'variant_id': str(variant.id),
            'quantity': 2
        }, format='json')

        assert response.status_code == 201

    def test_cannot_exceed_stock(self, authenticated_client, make_variant):
        client, user = authenticated_client
        variant = make_variant(stock_qty=5, price_override='100.00')

        response = client.post(reverse('cart-item-create'), {
            'variant_id': str(variant.id),
            'quantity': 10
        }, format='json')

        assert response.status_code == 400


@pytest.mark.django_db
class TestCartClear:
    def test_clear_cart(self, authenticated_client, make_variant):
        client, user = authenticated_client
        variant = make_variant(stock_qty=10, price_override='100.00')

        client.post(reverse('cart-item-create'), {
            'variant_id': str(variant.id),
            'quantity': 1
        }, format='json')

        response = client.delete(reverse('cart-clear'))
        assert response.status_code == 204
