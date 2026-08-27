from django.urls import path
from apps.wishlist import views

urlpatterns = [
    # GET  — view wishlist
    path('wishlist/', views.WishlistView.as_view()),
    path('wishlist/add/', views.WishlistItemAddView.as_view()
         ),             # POST — add item
    path('wishlist/clear/', views.WishlistClearView.as_view()
         ),             # DELETE — clear all
    # POST — move to cart
    path('wishlist/move-to-cart/', views.MoveToCartView.as_view()),
    # DELETE — remove one
    path('wishlist/<uuid:pk>/', views.WishlistItemDeleteView.as_view()),
]
