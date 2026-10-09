from decimal import Decimal, ROUND_HALF_UP

from django.core.cache import cache
from django.db import transaction
from django.db.models import F

from apps.cart.models import Cart, CartItem
from apps.cart.views import get_cart_cache_key
from apps.discounts.models import DiscountCode
from apps.orders.models import Order, OrderEvent, OrderItem
from apps.products.models import ProductVariant

TWO_PLACES = Decimal('0.01')


class CheckoutError(Exception):
    """An expected, user-facing checkout failure (maps to HTTP 400)."""


def create_order_from_cart(user, address, discount_code=None):
    """
    Turn the user's cart into a PENDING order, reserving stock.

    Concurrency design (all inside ONE transaction):
      1. Lock the user's Cart row first. Two concurrent checkouts by the same
         user (double-click, retry, two tabs) serialise here; the second one
         then sees an empty cart instead of buying everything twice.
      2. Lock all variant rows in ONE query ordered by primary key, so two
         checkouts with items in opposite order cannot deadlock.
      3. Validate stock, discount limits and minimum order against the LOCKED rows.
    No network I/O happens in here.
    """
    with transaction.atomic():
        cart = Cart.objects.select_for_update().filter(user=user).first()
        if cart is None:
            raise CheckoutError('Your cart is empty')

        items = list(CartItem.objects.filter(cart=cart).order_by('variant_id'))
        if not items:
            raise CheckoutError('Your cart is empty')

        variants = {
            v.pk: v for v in ProductVariant.objects
            .select_for_update(of=('self',))
            .select_related('product')
            .filter(pk__in=[i.variant_id for i in items])
            .order_by('pk')
        }

        subtotal = Decimal('0')
        lines = []
        for item in items:
            variant = variants[item.variant_id]
            if variant.stock_qty < item.quantity:
                raise CheckoutError(f'"{variant.product.name}" is out of stock')
            price = variant.effective_price
            subtotal += price * item.quantity
            lines.append((variant, item.quantity, price))

        discount, total = None, subtotal
        if discount_code:
            try:
                discount = DiscountCode.objects.select_for_update().get(
                    code=discount_code.strip().upper())
            except DiscountCode.DoesNotExist:
                raise CheckoutError('Invalid or expired discount code')
            if not discount.is_valid:
                raise CheckoutError('This discount code is invalid, expired or fully used')
            if subtotal < discount.min_order_amount:
                raise CheckoutError(
                    f'Minimum order amount for this code is GHS {discount.min_order_amount}')
            total = discount.apply_to(subtotal)
            DiscountCode.objects.filter(pk=discount.pk).update(
                used_count=F('used_count') + 1)
            code_cache_key = f'discount:{discount.code.upper()}'
            transaction.on_commit(lambda: cache.delete(code_cache_key))

        total = max(total, Decimal('0')).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        order = Order.objects.create(
            user=user,
            total_amount=total,
            shipping_address={
                'address_line': address.address_line1,
                'city': address.city,
                'region': address.region,
                'country': address.country,
            },
            discount=discount,
        )
        OrderItem.objects.bulk_create([
            OrderItem(order=order, variant=v, quantity=q, unit_price=p)
            for v, q, p in lines
        ])
        for variant, qty, _ in lines:
            ProductVariant.objects.filter(pk=variant.pk).update(
                stock_qty=F('stock_qty') - qty)
        OrderEvent.objects.create(
            order=order, status=Order.Status.PENDING,
            note='Order placed, awaiting payment')

        cart.items.all().delete()
        user_id = user.id
        transaction.on_commit(lambda: cache.delete(get_cart_cache_key(user_id)))

    return order
