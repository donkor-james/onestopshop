from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db.models import Avg, Count, Q
from apps.reviews.models import Review
from apps.reviews.serializers import ReviewSerializer, ProductRatingSummarySerializer
from apps.products.models import Product
from apps.orders.models import Order


class ProductReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Review.objects.none()
        return (
            Review.objects
            .filter(product__slug=self.kwargs['slug'])
            # select_related: user is a FK on Review —
            # loads user in same query to avoid N+1 when
            # get_user_name() accesses obj.user per review
            .select_related('user')
            .only(
                'id', 'rating', 'body',
                'is_verified_purchase', 'created_at',
                'user__first_name', 'user__last_name'
            )
            .order_by('-created_at')
        )

    def perform_create(self, serializer):
        product = Product.objects.only('id', 'name').get(
            slug=self.kwargs['slug']
        )

        # exists() — we don't need the review object, just know if one exists
        if Review.objects.filter(
            product=product, user=self.request.user
        ).exists():
            raise ValidationError('You have already reviewed this product')

        # Check verified purchase using exists() —
        # Q objects combine the conditions in a single DB query
        is_verified = Order.objects.filter(
            Q(user=self.request.user) &
            Q(items__variant__product=product) &
            Q(status='delivered')
        ).exists()

        if not is_verified:
            raise ValidationError(
                'You can only review products you have purchased and received'
            )

        serializer.save(
            user=self.request.user,
            product=product,
            is_verified_purchase=is_verified
        )


class ReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Review.objects.none()
        return Review.objects.filter(
            user=self.request.user
        ).select_related('user')


class ProductRatingSummaryView(generics.GenericAPIView):
    """
    Returns rating breakdown for a product.
    All computed in a single aggregation query — no Python loops.
    """
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = ProductRatingSummarySerializer  # ← add this

    def get(self, request, slug):
        # All aggregations run in ONE query using conditional Count
        # with Q objects — avoids querying the DB once per rating level
        summary = Review.objects.filter(
            product__slug=slug
        ).aggregate(
            avg_rating=Avg('rating'),
            review_count=Count('id'),
            five_star=Count('id', filter=Q(rating=5)),
            four_star=Count('id', filter=Q(rating=4)),
            three_star=Count('id', filter=Q(rating=3)),
            two_star=Count('id', filter=Q(rating=2)),
            one_star=Count('id', filter=Q(rating=1)),
        )

        serializer = ProductRatingSummarySerializer(summary)
        return Response(serializer.data)
