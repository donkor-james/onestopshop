from django.contrib import admin
from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'notification_type', 'title',
        'is_read', 'order_reference', 'created_at'
    ]
    list_filter = ['notification_type', 'is_read']
    search_fields = ['user__email', 'title', 'order_reference']
    readonly_fields = ['user', 'notification_type', 'order_reference']
