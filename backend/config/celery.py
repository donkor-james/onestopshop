import os
from celery import Celery
from dj_database_url import config

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production' if config(
    'ENVIRONMENT') == 'production' else 'config.settings.development')

app = Celery('backend')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
