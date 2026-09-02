from rest_framework import serializers
from apps.reviews.models import Review
from drf_spectacular.utils import extend_schema_field


class ReviewSerializer(serializers.ModelSerializer):
    # SerializerMethodField to avoid exposing full user object
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id', 'user_name', 'rating', 'body',
            'is_verified_purchase', 'created_at'
        ]
        read_only_fields = [
            'id', 'user_name', 'is_verified_purchase', 'created_at'
        ]

    @extend_schema_field(serializers.CharField())
    def get_user_name(self, obj):
        # obj.user is already select_related — no extra query here
        return f'{obj.user.first_name} {obj.user.last_name[0]}.'

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError('Rating must be between 1 and 5')
        return value


class ProductRatingSummarySerializer(serializers.Serializer):
    """
    Aggregated rating breakdown for a product.
    e.g. how many 5-stars, 4-stars etc.
    Returned by the rating summary endpoint.
    """
    avg_rating = serializers.FloatField()
    review_count = serializers.IntegerField()
    five_star = serializers.IntegerField()
    four_star = serializers.IntegerField()
    three_star = serializers.IntegerField()
    two_star = serializers.IntegerField()
    one_star = serializers.IntegerField()
