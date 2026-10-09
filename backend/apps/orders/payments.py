import logging
import uuid

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class PaymentGatewayError(Exception):
    """Paystack could not be reached or rejected the request."""


def initialize_payment(order, user, retry=False):
    """
    Start a Paystack transaction for `order` and return the hosted checkout URL.

    Must be called OUTSIDE a database transaction: it performs a network call
    with a 10s timeout and we never want to hold row locks while waiting on it.
    `retry=True` uses a fresh Paystack reference so a re-attempt can never
    collide with an earlier initialisation of the same order.
    """
    reference = order.reference if not retry else f'{order.reference}-R{uuid.uuid4().hex[:6]}'
    amount_in_pesewas = int((order.total_amount * 100).to_integral_value())

    try:
        response = requests.post(
            settings.PAYSTACK_INITIALIZE_URL,
            json={
                'email': user.email,
                'amount': amount_in_pesewas,
                'reference': reference,
                'metadata': {'order_id': str(order.id), 'user_id': str(user.id)},
            },
            headers={
                'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
                'Content-Type': 'application/json',
            },
            timeout=10,
        )
        body = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.exception('Paystack initialisation failed for order %s', order.reference)
        raise PaymentGatewayError('Payment gateway is unavailable.') from exc

    if response.status_code != 200 or not body.get('status'):
        logger.error('Paystack rejected initialisation for order %s: %s',
                     order.reference, body.get('message'))
        raise PaymentGatewayError('Payment gateway rejected the request.')

    return body['data']['authorization_url']
