# apps/orders/webhooks.py
import hmac
import hashlib
import json
from django.conf import settings
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from apps.orders.tasks import send_order_confirmation_email
from .models import Order


class PaystackWebhookView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        paystack_signature = request.headers.get("x-paystack-signature")

        if not paystack_signature:
            return Response({"error": "Missing signature"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Verify HMAC-SHA512 signature against raw body bytes
        raw_body = request.body
        expected_signature = hmac.new(
            key=settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
            msg=raw_body,
            digestmod=hashlib.sha512
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, paystack_signature):
            return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Parse Payload
        payload = json.loads(raw_body.decode("utf-8"))
        event_type = payload.get("event")

        # 3. Handle charge.success
        if event_type == "charge.success":
            data = payload.get("data", {})
            reference = data.get("reference")
            metadata = data.get("metadata", {})
            order_id = metadata.get("order_id")

            with transaction.atomic():
                try:
                    order = Order.objects.select_for_update().get(id=order_id)
                    if order.status != Order.Status.PAID:
                        order.status = Order.Status.PAID
                        order.paystack_reference = reference
                        order.save()

                        # Create an OrderEvent for the status change
                        order.events.create(
                            status=Order.Status.PAID,
                            note=f'Payment confirmed via Paystack webhook (ref: {reference})'
                        )

                        order_to_notify = order.id

                except Order.DoesNotExist:
                    return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

            if order_to_notify:
                send_order_confirmation_email.delay(order_to_notify)

        return Response({"status": "success"}, status=status.HTTP_200_OK)
