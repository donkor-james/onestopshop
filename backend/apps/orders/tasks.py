from celery import shared_task
import resend
from django.conf import settings
import logging

resend.api_key = settings.RESEND_API_KEY

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_confirmation_email(self, order_id):
    """
    Sends order confirmation email after successful checkout.
    Triggered from the checkout view, not called directly.
    """
    try:
        from apps.orders.models import Order

        order = Order.objects.select_related('user').get(id=order_id)

        resend.Emails.send({
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [order.user.email],
            "subject": f'Order Confirmed — #{order.reference}',
            "text": f"""
                Hi {order.user.first_name},

                Your order #{order.reference} has been confirmed.
                Total: GHS {order.total_amount}

                We will notify you once your order ships.

                Thank you for shopping with us.
            """,
        })

        print(f'Email sent for order {order.reference} to {order.user.email}')
        logger.info(
            f'Order confirmation email sent for order {order.reference}')
        return f'Email sent for order {order.reference} to {order.user.email}'

    except Exception as exc:
        print(f'Failed to send email for order {order_id}: {exc}')
        logger.error(f'Failed to send email for order {order_id}: {exc}')
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_shipping_update_email(self, order_id):
    """
    Triggered when order status changes to 'shipped'.
    """
    try:
        from apps.orders.models import Order

        order = Order.objects.select_related('user').get(id=order_id)

        resend.Emails.send({
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [order.user.email],
            "subject": f'Your Order #{order.reference} Has Shipped',
            "text": f"""
                Hi {order.user.first_name},

                Great news! Your order #{order.reference} is on its way.

                Thank you for shopping with us.
            """,
        })

        print(f'Shipping update email sent for order {order.reference}')
        logger.info(f'Shipping update email sent for order {order.reference}')

    except Exception as exc:
        print(f'Failed to send shipping email for order {order_id}: {exc}')
        logger.error(
            f'Failed to send shipping email for order {order_id}: {exc}')
        raise self.retry(exc=exc)


@shared_task
def cancel_unpaid_orders(max_age_minutes=30):
    """
    Release stock held by orders that were never paid.

    Each order is locked and re-checked, so this cannot race with the Paystack
    webhook: whichever takes the row lock first wins, and the other sees the
    new status and backs off.
    """
    from datetime import timedelta

    from django.db import transaction
    from django.db.models import F
    from django.utils import timezone

    from apps.discounts.models import DiscountCode
    from apps.orders.models import Order
    from apps.products.models import ProductVariant

    cutoff = timezone.now() - timedelta(minutes=max_age_minutes)
    stale_ids = list(
        Order.objects.filter(status=Order.Status.PENDING,
                             created_at__lt=cutoff)
        .values_list('id', flat=True)[:500])

    cancelled = 0
    for order_id in stale_ids:
        with transaction.atomic():
            order = Order.objects.select_for_update().filter(
                id=order_id, status=Order.Status.PENDING).first()
            if order is None:
                continue
            for item in order.items.order_by('variant_id'):
                ProductVariant.objects.filter(pk=item.variant_id).update(
                    stock_qty=F('stock_qty') + item.quantity)
            if order.discount_id:
                DiscountCode.objects.filter(pk=order.discount_id, used_count__gt=0).update(
                    used_count=F('used_count') - 1)
            order.status = Order.Status.CANCELLED
            order.save(update_fields=['status', 'updated_at'])
            order.events.create(
                status=Order.Status.CANCELLED,
                note='Cancelled automatically: payment not received in time')
            cancelled += 1
    logger.info('Cancelled %s unpaid orders', cancelled)
    return cancelled


@shared_task
def delete_old_idempotency_keys(hours=24):
    from datetime import timedelta

    from django.utils import timezone

    from apps.orders.models import IdempotencyKey

    deleted, _ = IdempotencyKey.objects.filter(
        created_at__lt=timezone.now() - timedelta(hours=hours)).delete()
    return deleted
