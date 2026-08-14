from django.urls import path
from . import views

urlpatterns = [
    path("products/<slug:slug>/reviews/", views.ProductReviewListCreateView.as_view(),
         name="product-review-list-create"),
    path("reviews/<uuid:pk>/", views.ReviewDetailView.as_view(),
         name="review-detail"),
    path("product-rating-summary/<slug:slug>/", views.ProductRatingSummaryView.as_view(),
         name="product-rating-summary"),
]
