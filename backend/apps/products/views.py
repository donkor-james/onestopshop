from rest_framework import generics, filters
from rest_framework.permissions import IsAdminUser, AllowAny, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Avg, Count, Min, Sum, Prefetch
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from apps.products.models import Category, Product, ProductImage, ProductVariant
from apps.products.serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer
)
from apps.reviews.serializers import ReviewSerializer
from apps.reviews.models import Review


class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Category.objects.none()
        return (
            Category.objects.all()
            # Count subcategories directly in the query —
            # no need to call subcategories.count() per category in Python
            .annotate(subcategory_count=Count('subcategories'))
            .only('id', 'name', 'slug', 'parent')
            .order_by('name')
        )

    # Categories almost never change — cache for 1 hour
    @method_decorator(cache_page(60 * 60))
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


class CategoryDetailView(generics.RetrieveAPIView):
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Category.objects.none()
        return (
            Category.objects.all()
            .annotate(subcategory_count=Count('subcategories'))
            .only('id', 'name', 'slug', 'parent')
        )

    @method_decorator(cache_page(60 * 60))
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


class ProductListView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category__slug', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['base_price', 'created_at', 'avg_rating', 'min_price']
    ordering = ['-created_at']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Product.objects.none()
        return (
            Product.objects.filter(is_active=True)
            .select_related('category')
            .prefetch_related(
                Prefetch(
                    'variants',
                    # Only prefetch the FIRST variant's primary image
                    # for the listing card — no need for all variants here
                    queryset=ProductVariant.objects.prefetch_related(
                        Prefetch(
                            'images',
                            queryset=ProductImage.objects.filter(
                                is_primary=True)
                        )
                    )
                )
            )
            .annotate(
                avg_rating=Avg('reviews__rating'),
                review_count=Count('reviews', distinct=True),
                min_price=Min('variants__price_override')
            )
            .only(
                'id', 'name', 'slug', 'base_price',
                'category', 'is_active', 'created_at'
            )
        )
    # Cache listing for 5 minutes — busted in signals.py when a product is saved

    @method_decorator(cache_page(60 * 5))
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

# products/views.py


@extend_schema(
    tags=['Products'],
    summary='Product detail',
    description=''
)
class ProductDetailView(generics.RetrieveAPIView):
    serializer_class = ProductDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Product.objects.none()
        return (
            Product.objects.filter(is_active=True)
            .select_related('category')
            .prefetch_related(
                Prefetch(
                    'variants',
                    # All variants with ALL their images for the detail page
                    queryset=ProductVariant.objects.prefetch_related(
                        Prefetch(
                            'images',
                            queryset=ProductImage.objects.order_by('order')
                        )
                    )
                )
            )
            .annotate(
                avg_rating=Avg('reviews__rating'),
                review_count=Count('reviews', distinct=True),
                total_stock=Sum('variants__stock_qty')
            )
        )

    @method_decorator(cache_page(60 * 10))
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


class ProductReviewListView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Review.objects.none()
        return (
            Review.objects.filter(
                product__slug=self.kwargs['slug']
            )
            .select_related('user')
            .only(
                'id', 'rating', 'body',
                'is_verified_purchase', 'created_at',
                'user__first_name', 'user__last_name'
            )
            .order_by('-created_at')
        )
