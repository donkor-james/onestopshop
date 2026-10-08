from django.urls import path
from . import views, webhook

urlpatterns = [
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('orders/<str:reference>/',
         views.OrderDetailView.as_view(), name='order-detail'),
    path("webhooks/paystack/", webhook.PaystackWebhookView.as_view(),
         name="paystack-webhook"),
]
