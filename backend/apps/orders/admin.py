from django.contrib import admin
from apps.orders.models import Order, OrderItem, OrderEvent


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['variant', 'quantity', 'unit_price']


class OrderEventInline(admin.TabularInline):
    model = OrderEvent
    extra = 0
    readonly_fields = ['status', 'note', 'created_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['reference', 'user',
                    'status', 'total_amount', 'created_at']
    list_filter = ['status']
    search_fields = ['reference', 'user__email']
    readonly_fields = ['reference', 'total_amount', 'shipping_address']
    inlines = [OrderItemInline, OrderEventInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
