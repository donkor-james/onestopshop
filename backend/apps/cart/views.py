from django.db.models.functions import Coalesce
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.core.cache import cache
from django.db.models import F, Sum, Count, ExpressionWrapper, DecimalField, Prefetch
from apps.cart.models import Cart, CartItem
from apps.cart.serializers import CartSerializer, CartItemSerializer
from apps.products.models import ProductVariant, ProductImage
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse


def get_cart_cache_key(user_id):
    return f'cart:{user_id}'


class CartView(generics.RetrieveAPIView):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        cache_key = get_cart_cache_key(request.user.id)
        cached = cache.get(cache_key)

        if cached:
            # Return cached serialized data directly
            print("Returning cached cart data")
            return Response(cached)

        cart, _ = Cart.objects.prefetch_related(
            Prefetch(
                'items',
                queryset=CartItem.objects.select_related(
                    'variant__product'
                ).prefetch_related(
                    Prefetch(
                        'variant__images',
                        queryset=ProductImage.objects.filter(is_primary=True)
                    )
                )
            )
        ).annotate(
            total=Sum(
                ExpressionWrapper(
                    F('items__quantity') * Coalesce(
                        F('items__variant__price_override'),
                        F('items__variant__product__base_price')
                    ),
                    output_field=DecimalField()
                )
            ),
            item_count=Count('items')
        ).get_or_create(user=request.user)
        serializer = self.get_serializer(cart)

        cache.set(cache_key, serializer.data, timeout=60 * 15)
        return Response(serializer.data)


class CartItemAddView(generics.CreateAPIView):
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        variant_id = serializer.validated_data['variant_id']
        quantity = serializer.validated_data['quantity']

        variant = ProductVariant.objects.select_related('product').prefetch_related(
            'images'
        ).get(id=variant_id)

        if variant.stock_qty < quantity:
            raise ValidationError('Not enough stock available')

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={'quantity': quantity}
        )

        if not created:
            CartItem.objects.filter(pk=cart_item.pk).update(
                quantity=F('quantity') + quantity
            )
            # Refresh from DB so the serializer gets the updated quantity
            cart_item.refresh_from_db()

        # Bust cart cache
        cache.delete(get_cart_cache_key(request.user.id))

        # Serialize the actual saved CartItem instance — not validated_data
        response_serializer = CartItemSerializer(
            cart_item,
            context={'request': request}
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class CartItemUpdateView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return CartItem.objects.none()
        return CartItem.objects.filter(
            cart__user=self.request.user
        ).select_related('variant__product')

    def perform_update(self, serializer):
        serializer.save()
        cache.delete(get_cart_cache_key(self.request.user.id))

    def perform_destroy(self, instance):
        instance.delete()
        cache.delete(get_cart_cache_key(self.request.user.id))


@extend_schema(
    tags=['Cart'],
    summary='Clear cart',
    description='Removes all items from the cart in a single DELETE query.',
    request=None,
    responses={204: OpenApiResponse(description='Cart cleared')}
)
class CartClearView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        CartItem.objects.filter(cart__user=request.user).delete()
        cache.delete(get_cart_cache_key(request.user.id))
        return Response(status=status.HTTP_204_NO_CONTENT)
