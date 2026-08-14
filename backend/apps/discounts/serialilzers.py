from rest_framework import serializers
from django.utils import timezone
from apps.discounts.models import DiscountCode


class DiscountCodeSerializer(serializers.ModelSerializer):
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = DiscountCode
        fields = [
            'id', 'code', 'discount_type', 'value',
            'min_order_amount', 'valid_until', 'is_valid'
        ]


class ApplyDiscountSerializer(serializers.Serializer):
    code = serializers.CharField()
    cart_total = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate(self, attrs):
        code = attrs['code'].upper()
        cart_total = attrs['cart_total']
        cache_key = f'discount:{code}'

        from django.core.cache import cache
        discount = cache.get(cache_key)

        if discount is None:
            try:
                discount = DiscountCode.objects.only(
                    'id', 'code', 'discount_type', 'value',
                    'min_order_amount', 'usage_limit',
                    'used_count', 'valid_from', 'valid_until', 'is_active'
                ).get(
                    code=code,
                    is_active=True,
                    valid_from__lte=timezone.now(),
                    valid_until__gte=timezone.now()
                )
                cache.set(cache_key, discount, timeout=60 * 5)
            except DiscountCode.DoesNotExist:
                raise serializers.ValidationError(
                    {'code': 'Invalid or expired discount code'}
                )

        if discount.usage_limit and discount.used_count >= discount.usage_limit:
            raise serializers.ValidationError(
                {'code': 'This discount code has reached its usage limit'}
            )

        if cart_total < discount.min_order_amount:
            raise serializers.ValidationError({
                'code': f'Minimum order amount is GHS {discount.min_order_amount}'
            })

        attrs['discount'] = discount
        return attrs
