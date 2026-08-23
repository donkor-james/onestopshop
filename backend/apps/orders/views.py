from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Count, F, Prefetch
from django.utils import timezone
from apps.orders.models import Order, OrderItem, OrderEvent
from apps.orders.serializers import OrderSerializer, CheckoutSerializer
from apps.orders.tasks import send_order_confirmation_email
from apps.cart.models import Cart, CartItem
from apps.accounts.models import Address
from apps.discounts.models import DiscountCode


class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
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
                # prefetch events for audit log — already ordered by created_at
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

    def post(self, request):
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        # Fetch cart with all related data upfront —
        # one query with joins rather than multiple queries inside the transaction
        cart = (
            Cart.objects
            .prefetch_related(
                Prefetch(
                    'items',
                    queryset=CartItem.objects.select_related(
                        'variant__product'
                    )
                )
            )
            .filter(user=request.user)
            .first()
        )

        if not cart or not cart.items.exists():
            return Response(
                {'error': 'Your cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )

        address = Address.objects.only(
            'address_line1', 'city', 'region', 'country'
        ).get(id=serializer.validated_data['address_id'])

        discount = None
        discount_code = serializer.validated_data.get('discount_code')

        try:
            with transaction.atomic():
                # Calculate total in Python from already-fetched cart items —
                # no extra query needed since we prefetched everything above
                total = sum(
                    item.variant.effective_price * item.quantity
                    for item in cart.items.all()
                )

                if discount_code:
                    # select_for_update() locks this discount row —
                    # prevents two simultaneous checkouts both reading
                    # used_count=9 and both thinking they're the 10th use
                    # when limit is 10
                    discount = DiscountCode.objects.select_for_update().get(
                        code=discount_code.upper(),
                        is_active=True,
                        valid_until__gte=timezone.now()
                    )
                    total = discount.apply_to(total)

                    # F() at DB level — avoids race condition on used_count
                    DiscountCode.objects.filter(pk=discount.pk).update(
                        used_count=F('used_count') + 1
                    )

                order = Order.objects.create(
                    user=request.user,
                    total_amount=max(total, 0),
                    shipping_address={
                        'address_line': address.address_line1,
                        'city': address.city,
                        'region': address.region,
                        'country': address.country,
                    },
                    discount=discount
                )

                # Validate stock and build order items list
                order_items = []
                variant_updates = []

                for item in cart.items.all():
                    # select_for_update() already applied via prefetch above —
                    # re-fetch just the variants that need stock deduction
                    variant = (
                        item.variant.__class__.objects
                        .select_for_update()
                        .get(pk=item.variant.pk)
                    )

                    if variant.stock_qty < item.quantity:
                        raise ValueError(
                            f'"{item.variant.product.name}" is out of stock'
                        )

                    order_items.append(OrderItem(
                        order=order,
                        variant=variant,
                        quantity=item.quantity,
                        unit_price=variant.effective_price
                    ))

                    variant_updates.append((variant.pk, item.quantity))

                # bulk_create: inserts all order items in ONE query
                # instead of one INSERT per item
                OrderItem.objects.bulk_create(order_items)

                # Update stock using F() for each variant —
                # DB-level decrement, no race condition
                for variant_pk, qty in variant_updates:
                    item.variant.__class__.objects.filter(
                        pk=variant_pk
                    ).update(stock_qty=F('stock_qty') - qty)

                # Record first order event
                OrderEvent.objects.create(
                    order=order,
                    status=Order.Status.PENDING,
                    note='Order placed successfully'
                )

                # Clear cart in one DELETE query
                cart.items.all().delete()

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Outside atomic block — only reaches here if everything committed
        send_order_confirmation_email.delay(order.id)

        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED
        )
