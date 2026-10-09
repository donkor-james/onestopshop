from .development import *
from decouple import config

DEBUG = False

# Remove the debug toolbar, which slows every request
INSTALLED_APPS = [a for a in INSTALLED_APPS if a != 'debug_toolbar']
MIDDLEWARE = [m for m in MIDDLEWARE if 'debug_toolbar' not in m]

# Set NO_CACHE=1 to measure without Redis caching
if config('NO_CACHE', default=False, cast=bool):
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
