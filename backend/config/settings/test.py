import tempfile
from .base import *

# --- Fast password hashing (bcrypt is slow by design, MD5 is fine for tests) ---
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# --- Test database ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='fashion_store_test'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# --- In-memory cache so tests don't touch real Redis ---
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# --- Emails captured in memory, never sent ---
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# --- Celery runs tasks synchronously (no broker needed) ---
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# --- Channels (in-memory layer, no Redis needed) ---
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

# --- Media files go to a temp dir ---
MEDIA_ROOT = tempfile.mkdtemp()


# test.py
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
