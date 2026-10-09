import hashlib
import hmac
import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.orders.models import Order, OrderItem
from apps.orders.tasks import cancel_unpaid_orders
from conftest import UserFactory, VariantFactory


def make_order(status=Order.Status.PENDING, total='250.00', variant=None, qty=1):
    user = UserFactory()
    order = Order.objects.create(
        user=user, total_amount=total, status=status,
        shipping_address={'city': 'Accra'})
    if variant:
        OrderItem.objects.create(order=order, variant=variant, quantity=qty, unit_price=total)
    return order


def deliver(order, amount=25000, event='charge.success', signature=None, metadata=True):
    body = json.dumps({
        'event': event,
        'data': {'reference': order.reference, 'amount': amount,
                 'metadata': {'order_id': str(order.id)} if metadata else None},
    }).encode()
    sig = signature or hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode(), body, hashlib.sha512).hexdigest()
    client = APIClient()
    return client.post(reverse('paystack-webhook'), data=body,
                       content_type='application/json', HTTP_X_PAYSTACK_SIGNATURE=sig)


@pytest.fixture
def email():
    with patch('apps.orders.webhook.send_order_confirmation_email.delay') as delay:
        yield delay


@pytest.mark.django_db
class TestPaystackWebhook:
    def test_rejects_missing_and_bad_signatures(self, email):
        order = make_order()
        client = APIClient()
        assert client.post(reverse('paystack-webhook'), data=b'{}',
                           content_type='application/json').status_code == 400
        assert deliver(order, signature='0' * 128).status_code == 400
        order.refresh_from_db()
        assert order.status == Order.Status.PENDING

    def test_marks_order_paid_once(self, email, django_capture_on_commit_callbacks):
        order = make_order()
        with django_capture_on_commit_callbacks(execute=True):
            assert deliver(order).status_code == 200
        order.refresh_from_db()
        assert order.status == Order.Status.PAID
        assert order.paystack_reference == order.reference
        assert order.events.filter(status=Order.Status.PAID).count() == 1
        email.assert_called_once_with(str(order.id))

    def test_duplicate_delivery_is_acknowledged_and_does_nothing(
            self, email, django_capture_on_commit_callbacks):
        order = make_order()
        with django_capture_on_commit_callbacks(execute=True):
            first = deliver(order)
            second = deliver(order)
            third = deliver(order)
        assert (first.status_code, second.status_code, third.status_code) == (200, 200, 200)
        assert order.events.filter(status=Order.Status.PAID).count() == 1
        assert email.call_count == 1

    def test_wrong_amount_does_not_mark_paid(self, email):
        order = make_order(total='250.00')
        assert deliver(order, amount=100).status_code == 200
        order.refresh_from_db()
        assert order.status == Order.Status.PENDING

    def test_unknown_order_and_missing_metadata_return_200(self, email):
        order = make_order()
        order.delete()
        assert deliver(order).status_code == 200
        assert deliver(make_order(), metadata=False).status_code == 200

    def test_other_events_are_ignored(self, email):
        order = make_order()
        assert deliver(order, event='transfer.success').status_code == 200
        order.refresh_from_db()
        assert order.status == Order.Status.PENDING

    def test_payment_for_cancelled_order_is_not_resurrected(self, email):
        order = make_order(status=Order.Status.CANCELLED)
        assert deliver(order).status_code == 200
        order.refresh_from_db()
        assert order.status == Order.Status.CANCELLED


@pytest.mark.django_db
class TestCancelUnpaidOrders:
    def test_stale_pending_order_is_cancelled_and_stock_restored(self):
        variant = VariantFactory(stock_qty=7)
        order = make_order(variant=variant, qty=3)
        Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(hours=1))

        assert cancel_unpaid_orders() == 1

        order.refresh_from_db()
        variant.refresh_from_db()
        assert order.status == Order.Status.CANCELLED
        assert variant.stock_qty == 10

    def test_recent_and_paid_orders_are_untouched(self):
        recent = make_order()
        paid = make_order(status=Order.Status.PAID)
        Order.objects.filter(pk=paid.pk).update(created_at=timezone.now() - timedelta(hours=5))
        assert cancel_unpaid_orders() == 0
        recent.refresh_from_db(); paid.refresh_from_db()
        assert recent.status == Order.Status.PENDING
        assert paid.status == Order.Status.PAID
