#!/usr/bin/env bash
# Render free tier: one web service has to do everything, so run the Celery
# worker (+ embedded Beat) in the background next to gunicorn.
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Worker consumes email tasks; -B embeds Beat so scheduled tasks fire while the
# service is awake. --pool=solo keeps memory low (free tier has 512 MB).
celery -A config worker -B --pool=solo --loglevel=info &

# exec so gunicorn receives Render's shutdown signals
exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1 --timeout 60
