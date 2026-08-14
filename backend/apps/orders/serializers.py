from rest_framework import serializers
from apps.orders.models import Order, OrderItem, OrderEvent


class OrderEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderEvent
        fields = ['id', 'status', 'note', 'created_at']


class OrderItemSerializer(serializers.ModelSerializer):
    # source traversal: variant → product → name
    # variant is select_related so no extra query
    product_name = serializers.CharField(
        source='variant.product.name', read_only=True
    )
    size = serializers.CharField(source='variant.size', read_only=True)
    color = serializers.CharField(source='variant.color', read_only=True)
    subtotal = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_name', 'size', 'color',
            'quantity', 'unit_price', 'subtotal'
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    events = OrderEventSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'reference', 'status', 'total_amount',
            'shipping_address', 'items', 'events',
            'item_count', 'created_at'
        ]
        read_only_fields = [
            'id', 'reference', 'status',
            'total_amount', 'created_at'
        ]


class CheckoutSerializer(serializers.Serializer):
    address_id = serializers.UUIDField()
    discount_code = serializers.CharField(required=False, allow_blank=True)

    def validate_address_id(self, value):
        from apps.accounts.models import Address
        # exists() — we only need to confirm ownership, not fetch the address yet
        if not Address.objects.filter(
            id=value, user=self.context['request'].user
        ).exists():
            raise serializers.ValidationError('Address not found')
        return value
