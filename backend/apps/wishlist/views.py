from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db.models import Count, Prefetch
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse
from apps.wishlist.models import Wishlist, WishlistItem
from apps.wishlist.serializers import (
    WishlistSerializer,
    WishlistItemSerializer,
    MoveToCartSerializer
)
from apps.cart.models import Cart, CartItem
from apps.products.models import Product, ProductImage
from django.db.models import F


class WishlistView(generics.RetrieveAPIView):
    """Get the current user's wishlist"""
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        wishlist, _ = Wishlist.objects.prefetch_related(
            Prefetch(
                'items',
                queryset=WishlistItem.objects.select_related(
                    'product'
                ).prefetch_related(
                    Prefetch(
                        'product__variants',
                        queryset=__import__(
                            'apps.products.models',
                            fromlist=['ProductVariant']
                        ).ProductVariant.objects.prefetch_related(
                            Prefetch(
                                'images',
                                queryset=ProductImage.objects.filter(
                                    is_primary=True
                                )
                            )
                        )
                    )
                ).order_by('-created_at')
            )
        ).annotate(
            item_count=Count('items')
        ).get_or_create(user=self.request.user)

        return wishlist


class WishlistItemAddView(generics.CreateAPIView):
    """Add a product to wishlist"""
    serializer_class = WishlistItemSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data['product_id']

        # Confirm product exists
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            raise ValidationError({'product_id': 'Product not found'})

        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)

        # exists() — fast check before attempting create
        if WishlistItem.objects.filter(
            wishlist=wishlist, product=product
        ).exists():
            raise ValidationError(
                {'product_id': 'Product already in wishlist'}
            )

        wishlist_item = WishlistItem.objects.create(
            wishlist=wishlist,
            product=product
        )

        return Response(
            WishlistItemSerializer(
                wishlist_item,
                context={'request': request}
            ).data,
            status=status.HTTP_201_CREATED
        )


class WishlistItemDeleteView(generics.DestroyAPIView):
    """Remove a product from wishlist"""
    permission_classes = [IsAuthenticated]
    serializer_class = WishlistItemSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return WishlistItem.objects.none()
        return WishlistItem.objects.filter(
            wishlist__user=self.request.user
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {'message': 'Item removed from wishlist'},
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags=['Wishlist'],
    summary='Clear wishlist',
    description='Removes all items from the wishlist.',
    request=None,
    responses={200: OpenApiResponse(description='Wishlist cleared')}
)
class WishlistClearView(APIView):  # ← APIView not GenericAPIView
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        deleted_count, _ = WishlistItem.objects.filter(
            wishlist__user=request.user
        ).delete()
        return Response(
            {'message': f'{deleted_count} items removed from wishlist'},
            status=status.HTTP_200_OK
        )


class MoveToCartView(generics.GenericAPIView):
    """
    Move a wishlist item to cart.
    Customer picks the specific variant (size/color) at this point.
    Optionally removes the item from the wishlist after moving.
    """
    serializer_class = MoveToCartSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        wishlist_item = serializer.validated_data['wishlist_item']
        variant = serializer.validated_data['variant']
        quantity = serializer.validated_data['quantity']

        # Get or create cart
        cart, _ = Cart.objects.get_or_create(user=request.user)

        # Add to cart — increase quantity if already exists
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={'quantity': quantity}
        )

        if not created:
            # F() — DB level increment, avoids race condition
            CartItem.objects.filter(pk=cart_item.pk).update(
                quantity=F('quantity') + quantity
            )
            cart_item.refresh_from_db()

        # Remove from wishlist after moving
        wishlist_item.delete()

        # Bust cart cache
        from apps.cart.views import get_cart_cache_key
        from django.core.cache import cache
        cache.delete(get_cart_cache_key(request.user.id))

        return Response({
            'message': f'{wishlist_item.product.name} moved to cart',
            'cart_item': {
                'variant_id': str(variant.id),
                'product_name': variant.product.name,
                'size': variant.size,
                'color': variant.color,
                'quantity': cart_item.quantity,
                'price': str(variant.effective_price)
            }
        }, status=status.HTTP_200_OK)
