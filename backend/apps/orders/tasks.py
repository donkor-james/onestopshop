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
