from django.urls import path
from .views import ApplyDiscountView

urlpatterns = [
    path('discounts/apply/', ApplyDiscountView.as_view(), name='apply-discount'),
]
