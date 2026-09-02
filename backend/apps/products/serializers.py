from rest_framework import serializers
from apps.products.models import Category, Product, ProductVariant, ProductImage
from drf_spectacular.utils import extend_schema_field


class CategorySerializer(serializers.ModelSerializer):
    subcategory_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent', 'subcategory_count']
        read_only_fields = ['id', 'slug']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'is_primary', 'order']


class ProductVariantSerializer(serializers.ModelSerializer):
    effective_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    is_in_stock = serializers.BooleanField(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = ProductVariant
        fields = [
            'id', 'size', 'color', 'sku', 'stock_qty',
            'price_override', 'effective_price', 'is_in_stock', 'images'
        ]
        read_only_fields = ['id']


class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    avg_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    total_stock = serializers.IntegerField(read_only=True)
    colors = serializers.SerializerMethodField()
    sizes = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'base_price',
            'category', 'variants', 'avg_rating', 'review_count',
            'total_stock', 'is_active', 'created_at',
            'colors', 'sizes'
        ]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_colors(self, obj):
        seen = set()
        colors = []
        for variant in obj.variants.all():
            if variant.stock_qty < 1:
                continue
            if variant.color not in seen:
                seen.add(variant.color)
                colors.append(variant.color)
        return colors

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_sizes(self, obj):
        seen = set()
        sizes = []
        for variant in obj.variants.all():
            if variant.stock_qty < 1:
                continue
            if variant.size not in seen:
                seen.add(variant.size)
                sizes.append(variant.size)
        return sizes


class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source='category.name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    avg_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    min_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'base_price', 'min_price',
            'category_name', 'primary_image', 'avg_rating', 'review_count'
        ]

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_primary_image(self, obj):
        # Variants and their images are already prefetched —
        # no extra query here
        first_variant = obj.variants.all().first()
        if not first_variant:
            return None
        for image in first_variant.images.all():
            if image.is_primary:
                return image.image.url
        return None
