from django.urls import path
from . import views

urlpatterns = [
    path("cart/", views.CartView.as_view(), name="cart"),
    path("cart/items/", views.CartItemAddView.as_view(),
         name="cart-item-create"),
    path("cart/items/<uuid:pk>/", views.CartItemUpdateView.as_view(),
         name="cart-item-detail"),
    path("cart/clear/", views.CartClearView.as_view(), name="cart-clear"),
]
