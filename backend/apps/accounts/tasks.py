from django.core.mail import send_mail
from django.conf import settings
import logging

try:
    from celery import shared_task
except ImportError:
    def shared_task(*decorator_args, **decorator_kwargs):
        def decorator(func):
            func.delay = func
            return func

        return decorator

logger = logging.getLogger(__name__)


@shared_task(name='send_otp_code')
def send_otp_code(user, otp):

    subject = "OneStopShop Email Verification"
    message = f"""
Hello, {user.first_name}\n
Welcome to OneStopShop!
Your OTP is {otp}.\n
It’s valid for 10 minutes. Enter this OTP to complete your account signup \n

The OneStopShop Team.
"""
    try:
        send_mail(subject=subject, message=message, from_email=settings.EMAIL_HOST_USER,
                  recipient_list=[user.email], fail_silently=False)
        logger.info(f"OTP email sent to {user.email} with OTP: {otp}")
    except Exception as e:
        logger.error(f"Failed to send OTP email to {user.email}: {e}")
