from rest_framework import serializers
from apps.cart.models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    # Read fields — come from select_related, no extra queries
    product_name = serializers.CharField(
        source='variant.product.name', read_only=True
    )
    size = serializers.CharField(source='variant.size', read_only=True)
    color = serializers.CharField(source='variant.color', read_only=True)
    # effective_price is a property on the model — no DB query
    effective_price = serializers.DecimalField(
        source='variant.effective_price',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    item_total = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    product_image = serializers.SerializerMethodField()
    stock_qty = serializers.IntegerField(
        source='variant.stock_qty', read_only=True
    )

    # Write field — used when adding to cart
    variant_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = CartItem
        fields = [
            'id', 'variant_id', 'product_name', 'size', 'color',
            'effective_price', 'item_total', 'quantity',
            'product_image', 'stock_qty'
        ]
        read_only_fields = ['id']

    def get_product_image(self, obj):
        # All images belong to variants now — no product-level images
        image = next(
            (img for img in obj.variant.images.all() if img.is_primary),
            None
        )
        return image.image.url if image else None

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError('Quantity must be at least 1')
        return value


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    # These come from annotations on the queryset
    total = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total', 'item_count', 'updated_at']
