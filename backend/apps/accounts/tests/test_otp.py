import json
from unittest.mock import patch
import pytest
from django.core.cache import cache
from django.urls import reverse
from conftest import UserFactory


@pytest.mark.django_db
class TestOtp:
    def test_register_hands_celery_only_json_serialisable_arguments(self, api_client):
        """A User instance in .delay() raises EncodeError once Celery is not in eager mode."""
        with patch('apps.accounts.views.send_otp_code.delay') as delay:
            response = api_client.post(reverse('register'), {
                'email': 'new@example.com', 'first_name': 'New', 'last_name': 'User',
                'password': 'Str0ng-pass-123', 'confirm_password': 'Str0ng-pass-123',
            }, format='json')
        assert response.status_code == 201
        json.dumps(list(delay.call_args.args))  # must not raise

    def test_otp_is_invalidated_after_five_wrong_guesses(self, api_client):
        user = UserFactory(is_active=False)
        cache.set(f'otp:{user.email}', '123456', timeout=600)

        for _ in range(5):
            r = api_client.post(
                reverse('verify-otp'), {'email': user.email, 'otp': '000000'}, format='json')
            assert r.status_code == 400
        blocked = api_client.post(
            reverse('verify-otp'), {'email': user.email, 'otp': '123456'}, format='json')

        assert blocked.status_code == 429  # even the correct code no longer works
        assert cache.get(f'otp:{user.email}') is None

    def test_correct_otp_still_activates_account(self, api_client):
        user = UserFactory(is_active=False)
        cache.set(f'otp:{user.email}', '123456', timeout=600)
        r = api_client.post(
            reverse('verify-otp'), {'email': user.email, 'otp': '123456'}, format='json')
        assert r.status_code == 200
        user.refresh_from_db()
        assert user.is_active
