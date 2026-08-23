from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def delete_old_notifications(self):
    """
    Deletes notifications older than 30 days.
    Runs every 24 hours via Celery beat.
    """
    try:
        from apps.notifications.models import Notification

        cutoff_date = timezone.now() - timedelta(days=30)
        deleted_count, _ = Notification.objects.filter(
            created_at__lt=cutoff_date
        ).delete()

        logger.info(f'Deleted {deleted_count} old notifications')
        return f'Deleted {deleted_count} notifications'

    except Exception as exc:
        logger.error(f'Failed to delete notifications: {exc}')
        raise self.retry(exc=exc, countdown=60 * 5)  # retry after 5 minutes
