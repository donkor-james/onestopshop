import hashlib
import json
from datetime import timedelta
from functools import wraps

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from apps.orders.models import IdempotencyKey

KEY_MAX_LENGTH = 128
# A claim stuck in "processing" longer than this is assumed to belong to a
# crashed worker and may be taken over.
STALE_AFTER = timedelta(minutes=5)


def _error(message, code):
    return Response({'error': message}, status=code)


def _claim(scope, request_hash):
    """Insert the key row. Returns (record, None) on success or (None, Response)."""
    for _ in range(3):
        try:
            with transaction.atomic():  # savepoint: an IntegrityError must not poison an outer transaction
                record = IdempotencyKey.objects.create(
                    request_hash=request_hash, **scope)
            return record, None
        except IntegrityError:
            existing = IdempotencyKey.objects.filter(**scope).first()
            if existing is None:
                continue  # released between our insert and our read; try again
            if existing.request_hash != request_hash:
                return None, _error(
                    'This Idempotency-Key was already used with a different request body.', 422)
            if existing.state == IdempotencyKey.State.COMPLETED:
                replay = Response(existing.response_body,
                                  status=existing.response_status)
                replay['Idempotent-Replayed'] = 'true'
                return None, replay
            if existing.created_at < timezone.now() - STALE_AFTER:
                IdempotencyKey.objects.filter(
                    pk=existing.pk, state=IdempotencyKey.State.PROCESSING).delete()
                continue
            return None, _error(
                'A request with this Idempotency-Key is still being processed.', 409)
    return None, _error('Could not acquire the Idempotency-Key. Please retry.', 409)


def idempotent(view_method):
    @wraps(view_method)
    def wrapper(self, request, *args, **kwargs):
        key = request.headers.get('Idempotency-Key', '').strip()
        if not key or len(key) > KEY_MAX_LENGTH:
            return _error(
                f'A valid Idempotency-Key header (max {KEY_MAX_LENGTH} characters) is required.', 400)

        body = json.dumps(request.data, sort_keys=True, default=str)
        request_hash = hashlib.sha256(body.encode()).hexdigest()
        scope = {'user': request.user, 'endpoint': request.path, 'key': key}

        record, early_response = _claim(scope, request_hash)
        if early_response is not None:
            return early_response

        try:
            response = view_method(self, request, *args, **kwargs)
        except Exception:
            record.delete()  # let the client retry
            raise

        if 200 <= response.status_code < 300:
            payload = (json.loads(JSONRenderer().render(response.data))
                       if response.data is not None else None)
            IdempotencyKey.objects.filter(pk=record.pk).update(
                state=IdempotencyKey.State.COMPLETED,
                response_status=response.status_code,
                response_body=payload)
        else:
            record.delete()
        return response
    return wrapper
