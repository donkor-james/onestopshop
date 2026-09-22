from django.contrib import admin
from apps.discounts.models import DiscountCode


@admin.register(DiscountCode)
class DiscountCodeAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'discount_type', 'value',
        'used_count', 'usage_limit', 'is_active', 'valid_until'
    ]
    list_filter = ['discount_type', 'is_active']
    search_fields = ['code']
    readonly_fields = ['used_count']
