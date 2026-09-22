import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from tests.factories import ProductFactory, VariantFactory, CategoryFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestProductList:
    def test_list_products_returns_200(self, api_client):
        ProductFactory.create_batch(3)
        response = api_client.get(reverse('product-list'))
        assert response.status_code == 200
        assert response.data['count'] == 3

    def test_inactive_products_not_shown(self, api_client):
        ProductFactory(is_active=True)
        ProductFactory(is_active=False)
        response = api_client.get(reverse('product-list'))
        assert response.data['count'] == 1

    def test_filter_by_category(self, api_client):
        category = CategoryFactory(name='Dresses')
        ProductFactory(category=category)
        ProductFactory()  # different category

        response = api_client.get(
            reverse('product-list'),
            {'category__slug': category.slug}
        )
        assert response.data['count'] == 1

    def test_search_by_name(self, api_client):
        ProductFactory(name='Red Floral Dress')
        ProductFactory(name='Blue Jeans')

        response = api_client.get(
            reverse('product-list'),
            {'search': 'floral'}
        )
        assert response.data['count'] == 1


@pytest.mark.django_db
class TestProductDetail:
    def test_product_detail_returns_variants(self, api_client):
        product = ProductFactory()
        VariantFactory(product=product, color='Red', size='M', stock_qty=5)
        VariantFactory(product=product, color='Blue', size='L', stock_qty=3)

        response = api_client.get(
            reverse('product-detail', kwargs={'slug': product.slug})
        )

        assert response.status_code == 200
        assert len(response.data['variants']) == 2

    def test_colors_only_shows_in_stock(self, api_client):
        product = ProductFactory()
        VariantFactory(product=product, color='Red', size='M', stock_qty=5)
        VariantFactory(product=product, color='Blue', size='M', stock_qty=0)

        response = api_client.get(
            reverse('product-detail', kwargs={'slug': product.slug})
        )

        assert 'Red' in response.data['colors']
        assert 'Blue' not in response.data['colors']

    def test_inactive_product_returns_404(self, api_client):
        product = ProductFactory(is_active=False)
        response = api_client.get(
            reverse('product-detail', kwargs={'slug': product.slug})
        )
        assert response.status_code == 404
