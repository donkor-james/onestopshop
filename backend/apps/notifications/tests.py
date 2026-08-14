from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count, Q
from apps.notifications.models import Notification
from apps.notifications.serializers import (
    NotificationSerializer,
    NotificationSummarySerializer
)


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Notification.objects.filter(
            user=self.request.user
        ).only(
            'id', 'notification_type', 'title',
            'message', 'is_read', 'order_reference', 'created_at'
        )

        # Optional filter by read status via query param
        # e.g. GET /notifications/?is_read=false
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')

        return queryset.order_by('-created_at')


class NotificationDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve or mark a single notification as read"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class MarkAllReadView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # update() on queryset — single UPDATE WHERE query,
        # no need to fetch each notification into Python
        updated = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)

        return Response({'marked_read': updated})


class NotificationSummaryView(generics.GenericAPIView):
    """
    Used by the frontend navbar bell icon.
    Returns total and unread count without fetching notification content.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Single aggregation query — no Python iteration
        # Q filter inside Count: counts only unread ones
        summary = Notification.objects.filter(
            user=request.user
        ).aggregate(
            total=Count('id'),
            unread_count=Count('id', filter=Q(is_read=False))
        )

        serializer = NotificationSummarySerializer(summary)
        return Response(serializer.data)


class DeleteReadNotificationsView(generics.GenericAPIView):
    """Let users clean up their own read notifications"""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        deleted_count, _ = Notification.objects.filter(
            user=request.user,
            is_read=True
        ).delete()

        return Response(
            {'deleted': deleted_count},
            status=status.HTTP_200_OK
        )
