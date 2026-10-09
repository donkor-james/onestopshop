"""
Real-concurrency tests. They need committed transactions (transaction=True) and
PostgreSQL, because SQLite has no row-level locking.
"""
import threading
import uuid

import pytest
from django.db import connection
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Address
from apps.cart.models import Cart, CartItem
from apps.discounts.models import DiscountCode
from apps.orders.models import Order
from conftest import DiscountCodeFactory, UserFactory, VariantFactory

pytestmark = pytest.mark.django_db(transaction=True)


def make_address(user):
    return Address.objects.create(
        user=user, address_line1='1 Test St', city='Accra',
        region='Greater Accra', country='Ghana', is_default=True)


def fill_cart(user, *lines):
    cart, _ = Cart.objects.get_or_create(user=user)
    for variant, qty in lines:
        CartItem.objects.create(cart=cart, variant=variant, quantity=qty)


def checkout_call(user, address, key=None, code=None):
    def call():
        client = APIClient()
        client.force_authenticate(user)
        body = {'address_id': str(address.id)}
        if code:
            body['discount_code'] = code
        return client.post(reverse('checkout'), body, format='json',
                           HTTP_IDEMPOTENCY_KEY=key or str(uuid.uuid4())).status_code
    return call


def run_together(calls):
    """Release all callables at the same instant; return their results in order."""
    results = [None] * len(calls)
    barrier = threading.Barrier(len(calls))

    def worker(i, call):
        try:
            barrier.wait()
            results[i] = call()
        except Exception as exc:  # surface crashes (e.g. deadlocks) as results
            results[i] = f'{type(exc).__name__}: {exc}'
        finally:
            connection.close()  # each thread owns its own DB connection

    threads = [threading.Thread(target=worker, args=(i, c)) for i, c in enumerate(calls)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    return results


def test_double_click_with_same_key_creates_one_order(paystack_ok):
    user, variant = UserFactory(), VariantFactory(stock_qty=10)
    address = make_address(user)
    fill_cart(user, (variant, 1))

    results = run_together([checkout_call(user, address, key='same')] * 2)

    assert set(results) <= {201, 409}, results
    assert Order.objects.filter(user=user).count() == 1
    variant.refresh_from_db()
    assert variant.stock_qty == 9


def test_two_tabs_with_different_keys_still_create_one_order(paystack_ok):
    """The cart lock, not the idempotency key, is what protects this case."""
    user, variant = UserFactory(), VariantFactory(stock_qty=10)
    address = make_address(user)
    fill_cart(user, (variant, 1))

    results = run_together([checkout_call(user, address), checkout_call(user, address)])

    assert sorted(results) == [201, 400], results
    assert Order.objects.filter(user=user).count() == 1
    variant.refresh_from_db()
    assert variant.stock_qty == 9


def test_no_overselling_under_concurrent_checkouts(paystack_ok):
    variant = VariantFactory(stock_qty=5)
    users = [UserFactory() for _ in range(20)]
    calls = []
    for u in users:
        fill_cart(u, (variant, 1))
        calls.append(checkout_call(u, make_address(u)))

    results = run_together(calls)

    assert results.count(201) == 5, results
    assert results.count(400) == 15, results
    variant.refresh_from_db()
    assert variant.stock_qty == 0
    assert Order.objects.count() == 5


def test_opposite_item_order_does_not_deadlock(paystack_ok):
    a, b = VariantFactory(stock_qty=1000), VariantFactory(stock_qty=1000)
    for _ in range(15):
        u1, u2 = UserFactory(), UserFactory()
        fill_cart(u1, (a, 1), (b, 1))
        fill_cart(u2, (b, 1), (a, 1))
        results = run_together([checkout_call(u1, make_address(u1)),
                                checkout_call(u2, make_address(u2))])
        assert results == [201, 201], results


def test_discount_usage_limit_holds_under_concurrency(paystack_ok):
    DiscountCodeFactory(code='LIMITED', usage_limit=3)
    calls = []
    for _ in range(10):
        u = UserFactory()
        fill_cart(u, (VariantFactory(stock_qty=5), 1))
        calls.append(checkout_call(u, make_address(u), code='LIMITED'))

    results = run_together(calls)

    assert results.count(201) == 3, results
    assert DiscountCode.objects.get(code='LIMITED').used_count == 3


def test_paystack_is_never_called_while_row_locks_are_held(paystack_ok):
    user, variant = UserFactory(), VariantFactory(stock_qty=5)
    address = make_address(user)
    fill_cart(user, (variant, 1))
    seen = []
    paystack_ok.side_effect = lambda *a, **k: (
        seen.append(connection.in_atomic_block), paystack_ok.return_value)[1]

    assert checkout_call(user, address)() == 201
    assert seen == [False]
