from rest_framework import serializers
from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title',
            'message', 'is_read', 'order_reference', 'created_at'
        ]
        read_only_fields = [
            'id', 'notification_type', 'title',
            'message', 'order_reference', 'created_at'
        ]


class NotificationSummarySerializer(serializers.Serializer):
    """
    Lightweight summary shown in the navbar bell icon.
    All computed via annotation — no extra queries.
    """
    total = serializers.IntegerField()
    unread_count = serializers.IntegerField()
