from rest_framework import serializers
from apps.wishlist.models import Wishlist, WishlistItem
from apps.products.models import ProductVariant
from drf_spectacular.utils import extend_schema_field


class WishlistItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source='product.name', read_only=True
    )
    product_slug = serializers.CharField(
        source='product.slug', read_only=True
    )
    base_price = serializers.DecimalField(
        source='product.base_price',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    primary_image = serializers.SerializerMethodField()
    is_in_stock = serializers.SerializerMethodField()
    product_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = WishlistItem
        fields = [
            'id', 'product_id', 'product_name', 'product_slug',
            'base_price', 'primary_image', 'is_in_stock', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_primary_image(self, obj):
        # Get first variant's primary image — already prefetched
        first_variant = obj.product.variants.all().first()
        if not first_variant:
            return None
        primary = next(
            (img for img in first_variant.images.all() if img.is_primary),
            None
        )
        return primary.image.url if primary else None

    @extend_schema_field(serializers.BooleanField())
    def get_is_in_stock(self, obj):
        # Check if any variant has stock — already prefetched
        return any(
            variant.stock_qty > 0
            for variant in obj.product.variants.all()
        )


class WishlistSerializer(serializers.ModelSerializer):
    items = WishlistItemSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Wishlist
        fields = ['id', 'items', 'item_count', 'created_at']


class MoveToCartSerializer(serializers.Serializer):
    """
    Used when moving a wishlist item to cart.
    Customer must pick a specific variant at this point.
    """
    wishlist_item_id = serializers.UUIDField()
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate(self, attrs):
        from apps.wishlist.models import WishlistItem
        request = self.context['request']

        # Confirm wishlist item belongs to this user
        try:
            wishlist_item = WishlistItem.objects.select_related(
                'product'
            ).get(
                id=attrs['wishlist_item_id'],
                wishlist__user=request.user
            )
        except WishlistItem.DoesNotExist:
            raise serializers.ValidationError(
                {'wishlist_item_id': 'Wishlist item not found'}
            )

        # Confirm variant belongs to the same product
        try:
            variant = ProductVariant.objects.select_related('product').get(
                id=attrs['variant_id'],
                product=wishlist_item.product
            )
        except ProductVariant.DoesNotExist:
            raise serializers.ValidationError(
                {'variant_id': 'Variant does not belong to this product'}
            )

        if variant.stock_qty < attrs['quantity']:
            raise serializers.ValidationError(
                {'quantity': 'Not enough stock available'}
            )

        attrs['wishlist_item'] = wishlist_item
        attrs['variant'] = variant
        return attrs
