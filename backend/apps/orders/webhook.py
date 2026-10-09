import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.orders.tasks import send_order_confirmation_email

logger = logging.getLogger(__name__)


def _ok(label='ok'):
    return Response({'status': label}, status=status.HTTP_200_OK)


class PaystackWebhookView(APIView):
    """
    Paystack delivers events at-least-once, so this handler must be idempotent.
    Rule: always answer 2xx for anything we have fully understood (including
    duplicates and events we deliberately ignore) - a non-2xx makes Paystack retry.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        signature = request.headers.get('x-paystack-signature')
        if not signature:
            return Response({'error': 'Missing signature'}, status=status.HTTP_400_BAD_REQUEST)

        raw_body = request.body
        expected = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode(
                'utf-8'), raw_body, hashlib.sha512
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return Response({'error': 'Invalid signature'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = json.loads(raw_body.decode('utf-8'))
        except ValueError:
            return Response({'error': 'Invalid JSON'}, status=status.HTTP_400_BAD_REQUEST)

        if payload.get('event') != 'charge.success':
            return _ok('ignored')

        data = payload.get('data') or {}
        reference = data.get('reference')
        order_id = (data.get('metadata') or {}).get('order_id')
        if not order_id:
            logger.warning(
                'charge.success without order_id (reference=%s)', reference)
            return _ok('ignored')

        with transaction.atomic():
            try:
                order = Order.objects.select_for_update().get(id=order_id)
            except (Order.DoesNotExist, DjangoValidationError, ValueError):
                logger.warning(
                    'charge.success for unknown order %s (reference=%s)', order_id, reference)
                return _ok('ignored')

            if order.status != Order.Status.PENDING:
                if order.status != Order.Status.PAID:
                    logger.error(
                        'Payment %s received for order %s in status %s - needs manual review/refund',
                        reference, order.reference, order.status)
                return _ok('already_processed')

            expected_amount = int(
                (order.total_amount * 100).to_integral_value())
            if data.get('amount') != expected_amount:
                logger.error('Amount mismatch for order %s: paid %s, expected %s',
                             order.reference, data.get('amount'), expected_amount)
                return _ok('amount_mismatch')

            order.status = Order.Status.PAID
            order.paystack_reference = reference
            order.save(update_fields=[
                       'status', 'paystack_reference', 'updated_at'])
            order.events.create(
                status=Order.Status.PAID,
                note=f'Payment confirmed via Paystack webhook (ref: {reference})')
            order_pk = str(order.id)
            transaction.on_commit(
                lambda: send_order_confirmation_email.delay(order_pk))

        return _ok()
