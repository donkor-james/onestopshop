import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestProductList:
    def test_list_products_returns_200(self, api_client, make_product):
        make_product()
        make_product()
        response = api_client.get(reverse('product-list'))
        assert response.status_code == 200
        assert response.data['count'] == 2

    def test_inactive_products_not_shown(self, api_client, make_product):
        make_product(is_active=True)
        make_product(is_active=False)
        response = api_client.get(reverse('product-list'))
        assert response.data['count'] == 1

    def test_search_by_name(self, api_client, make_product):
        make_product(name='Red Floral Dress')
        make_product(name='Blue Jeans')
        response = api_client.get(
            reverse('product-list'), {'search': 'floral'})
        assert response.data['count'] == 1


@pytest.mark.django_db
class TestProductDetail:
    def test_product_detail_returns_200(self, api_client, make_product, make_variant):
        product = make_product()
        make_variant(product=product)
        response = api_client.get(
            reverse('product-detail', kwargs={'slug': product.slug})
        )
        assert response.status_code == 200

    def test_inactive_product_returns_404(self, api_client, make_product):
        product = make_product(is_active=False)
        response = api_client.get(
            reverse('product-detail', kwargs={'slug': product.slug})
        )
        assert response.status_code == 404
