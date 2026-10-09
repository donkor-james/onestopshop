import pytest
from django.core.cache import cache
from django.urls import reverse

from apps.accounts.models import Address
from apps.cart.models import Cart, CartItem
from apps.cart.views import get_cart_cache_key
from apps.orders.models import IdempotencyKey, Order
from conftest import idem_key


def setup_cart(user, variant, quantity=1):
    cart, _ = Cart.objects.get_or_create(user=user)
    CartItem.objects.create(cart=cart, variant=variant, quantity=quantity)
    return cart


def create_address(user):
    return Address.objects.create(
        user=user, address_line1='12 Test Street', city='Accra',
        region='Greater Accra', country='Ghana', is_default=True)


def checkout(client, address, key=None, **body):
    headers = {'HTTP_IDEMPOTENCY_KEY': key} if key else idem_key()
    return client.post(reverse('checkout'),
                       {'address_id': str(address.id), **body},
                       format='json', **headers)


@pytest.mark.django_db
class TestCheckout:
    def test_creates_pending_order_and_returns_payment_url(
            self, authenticated_client, make_variant, paystack_ok):
        client, user = authenticated_client
        variant = make_variant(stock_qty=10, price_override='250.00')
        setup_cart(user, variant, quantity=2)

        response = checkout(client, create_address(user))

        assert response.status_code == 201
        assert response.data['checkout_url'] == 'https://checkout.paystack.test/abc'
        order = Order.objects.get(user=user)
        assert order.status == Order.Status.PENDING
        assert str(order.total_amount) == '500.00'
        # Paystack is told the amount in pesewas
        assert paystack_ok.call_args.kwargs['json']['amount'] == 50000

    def test_deducts_stock_and_clears_cart(
            self, authenticated_client, make_variant, paystack_ok):
        client, user = authenticated_client
        variant = make_variant(stock_qty=10)
        setup_cart(user, variant, quantity=3)

        checkout(client, create_address(user))

        variant.refresh_from_db()
        assert variant.stock_qty == 7
        assert Cart.objects.get(user=user).items.count() == 0

    def test_cart_cache_is_busted_after_checkout(
            self, authenticated_client, make_variant, paystack_ok,
            django_capture_on_commit_callbacks):
        client, user = authenticated_client
        setup_cart(user, make_variant(stock_qty=5))
        # primes the cache
        assert len(client.get(reverse('cart')).data['items']) == 1

        # pytest-django wraps tests in a transaction, so on_commit hooks only
        # run when we ask for them (in production they run at commit).
        with django_capture_on_commit_callbacks(execute=True):
            checkout(client, create_address(user))

        assert cache.get(get_cart_cache_key(user.id)) is None
        assert client.get(reverse('cart')).data['items'] == []

    def test_empty_cart_fails(self, authenticated_client, paystack_ok):
        client, user = authenticated_client
        assert checkout(client, create_address(user)).status_code == 400

    def test_prevents_overselling(self, authenticated_client, make_variant, paystack_ok):
        client, user = authenticated_client
        variant = make_variant(stock_qty=2)
        setup_cart(user, variant, quantity=5)

        response = checkout(client, create_address(user))

        assert response.status_code == 400
        variant.refresh_from_db()
        assert variant.stock_qty == 2
        assert Order.objects.count() == 0

    def test_gateway_failure_keeps_order_and_allows_retry(
            self, authenticated_client, make_variant, paystack_ok):
        import requests
        client, user = authenticated_client
        setup_cart(user, make_variant(stock_qty=5))
        paystack_ok.side_effect = requests.ConnectionError('boom')

        response = checkout(client, create_address(user))

        assert response.status_code == 201
        assert response.data['checkout_url'] is None
        assert 'payment_error' in response.data
        order = Order.objects.get(user=user)

        paystack_ok.side_effect = None
        retry = client.post(
            reverse('order-pay', kwargs={'reference': order.reference}))
        assert retry.status_code == 200
        assert retry.data['checkout_url']


@pytest.mark.django_db
class TestIdempotency:
    def test_missing_key_is_rejected(self, authenticated_client, make_variant, paystack_ok):
        client, user = authenticated_client
        setup_cart(user, make_variant(stock_qty=5))
        response = client.post(reverse('checkout'),
                               {'address_id': str(create_address(user).id)}, format='json')
        assert response.status_code == 400
        assert Order.objects.count() == 0

    def test_same_key_replays_original_response(
            self, authenticated_client, make_variant, paystack_ok):
        client, user = authenticated_client
        variant = make_variant(stock_qty=10)
        setup_cart(user, variant)
        address = create_address(user)

        first = checkout(client, address, key='key-1')
        second = checkout(client, address, key='key-1')

        assert first.status_code == second.status_code == 201
        assert second['Idempotent-Replayed'] == 'true'
        assert second.data['reference'] == first.data['reference']
        assert Order.objects.count() == 1
        assert paystack_ok.call_count == 1
        variant.refresh_from_db()
        assert variant.stock_qty == 9

    def test_same_key_different_body_is_422(
            self, authenticated_client, make_variant, paystack_ok):
        client, user = authenticated_client
        setup_cart(user, make_variant(stock_qty=10))
        address = create_address(user)
        checkout(client, address, key='key-2')
        other = create_address(user)
        assert checkout(client, other, key='key-2').status_code == 422

    def test_failed_attempt_releases_key_for_retry(
            self, authenticated_client, make_variant, paystack_ok):
        client, user = authenticated_client
        variant = make_variant(stock_qty=1)
        setup_cart(user, variant, quantity=3)
        address = create_address(user)
        assert checkout(client, address, key='key-3').status_code == 400
        assert not IdempotencyKey.objects.filter(key='key-3').exists()

        variant.stock_qty = 5
        variant.save()
        assert checkout(client, address, key='key-3').status_code == 201


@pytest.mark.django_db
class TestDiscounts:
    def test_valid_code_applies_and_counts_use(
            self, authenticated_client, make_variant, make_discount, paystack_ok):
        client, user = authenticated_client
        setup_cart(user, make_variant(stock_qty=5, price_override='100.00'))
        discount = make_discount(code='SAVE10', value=10, usage_limit=5)

        response = checkout(client, create_address(user),
                            discount_code='save10')

        assert response.status_code == 201
        assert str(Order.objects.get().total_amount) == '90.00'
        discount.refresh_from_db()
        assert discount.used_count == 1

    def test_exhausted_code_is_rejected(
            self, authenticated_client, make_variant, make_discount, paystack_ok):
        client, user = authenticated_client
        setup_cart(user, make_variant(stock_qty=5))
        make_discount(code='ONCE', usage_limit=1, used_count=1)
        assert checkout(client, create_address(user),
                        discount_code='ONCE').status_code == 400
        assert Order.objects.count() == 0

    def test_minimum_order_is_enforced(
            self, authenticated_client, make_variant, make_discount, paystack_ok):
        client, user = authenticated_client
        setup_cart(user, make_variant(stock_qty=5, price_override='100.00'))
        make_discount(code='BIG', min_order_amount=1000)
        assert checkout(client, create_address(user),
                        discount_code='BIG').status_code == 400

    def test_unknown_code_is_400_not_500(
            self, authenticated_client, make_variant, paystack_ok):
        client, user = authenticated_client
        setup_cart(user, make_variant(stock_qty=5))
        assert checkout(client, create_address(user),
                        discount_code='NOPE').status_code == 400
