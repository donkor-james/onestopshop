import logging
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.models import Address
from apps.orders.idempotency import idempotent
from apps.orders.models import Order, OrderEvent, OrderItem
from apps.orders.payments import PaymentGatewayError, initialize_payment
from apps.orders.serializers import CheckoutSerializer, OrderSerializer
from apps.orders.services import CheckoutError, create_order_from_cart


class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
        return (
            Order.objects
            .filter(user=self.request.user)
            # prefetch items with their variants and products in one go —
            # avoids N+1 when serializer loops through items
            .prefetch_related(
                Prefetch(
                    'items',
                    queryset=OrderItem.objects.select_related(
                        'variant__product'
                    ).only(
                        'id', 'quantity', 'unit_price',
                        'variant__size', 'variant__color',
                        'variant__product__name'
                    )
                )
            )
            # annotate item_count so serializer doesn't call .count() per order
            .annotate(item_count=Count('items'))
            # only() — skip fields not shown in list
            .only(
                'id', 'reference', 'status',
                'total_amount', 'created_at'
            )
            .order_by('-created_at')
        )


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'reference'

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
        return (
            Order.objects
            .filter(user=self.request.user)
            .select_related('discount')
            .prefetch_related(
                Prefetch(
                    'items',
                    queryset=OrderItem.objects.select_related(
                        'variant__product'
                    )
                ),
                # prefetch events for audit log
                Prefetch(
                    'events',
                    queryset=OrderEvent.objects.only(
                        'id', 'status', 'note', 'created_at'
                    )
                )
            )
            .annotate(item_count=Count('items'))
        )


class CheckoutView(generics.GenericAPIView):
    serializer_class = CheckoutSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Checkout',
        description="""
            Creates a PENDING order from the current cart and starts a Paystack payment.

            Requires an `Idempotency-Key` header (e.g. a UUID generated once per checkout
            attempt). Retrying with the same key and body returns the original response
            instead of creating a second order.

            Stock is reserved atomically; unpaid orders are cancelled and their stock
            released automatically after a timeout.
        """,
        responses={201: OrderSerializer}
    )
    @idempotent
    def post(self, request):
        serializer = self.get_serializer(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        address = Address.objects.get(
            id=serializer.validated_data['address_id'], user=request.user)

        try:
            order = create_order_from_cart(
                user=request.user,
                address=address,
                discount_code=serializer.validated_data.get('discount_code'),
            )
        except CheckoutError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # The order and stock reservation are committed at this point. The
        # external HTTP call happens OUTSIDE any transaction so no row locks
        # are held while we wait on Paystack.
        data = OrderSerializer(order).data
        try:
            data['checkout_url'] = initialize_payment(order, request.user)
        except PaymentGatewayError as exc:
            data['checkout_url'] = None
            data['payment_error'] = (
                f'{exc} Retry with POST /api/orders/{order.reference}/pay/')

        return Response(data, status=status.HTTP_201_CREATED)


class OrderPayView(APIView):
    """(Re)start payment for an order that is still pending."""
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Start or retry payment for a pending order',
                   request=None, responses={200: None})
    def post(self, request, reference):
        order = get_object_or_404(
            Order, reference=reference, user=request.user,
            status=Order.Status.PENDING)
        try:
            url = initialize_payment(order, request.user, retry=True)
        except PaymentGatewayError as exc:
            return Response({'error': str(exc)},
                            status=status.HTTP_502_BAD_GATEWAY)
        return Response({'checkout_url': url})
